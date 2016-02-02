"""Provide (basic) asynchronous control over a BMP responsible for controling a
whole rack.
"""

import threading

from collections import namedtuple, deque

from rig.links import Links
from rig.machine_control import BMPController

import logging

class PowerRequest(namedtuple("PowerRequest", "state board on_done")):
    """Reuqests that a specific board should have its power state set to a
    particular value.
    
    Attributes
    ----------
    state : bool
        On (True) or off (False).
    board : int
        Board to change the state of
    on_done : function()
        A function to call when the request has been completed.
    """

class LinkRequest(namedtuple("LinkRequest", "board link enable on_done")):
    """Reuqests that a specific board should have its power state set to a
    particular value.
    
    Attributes
    ----------
    board : int
        Board whose link should be blocked/unblocked
    link : :py:class:`rig.links.Link`
        The link whose state should be changed
    enable : bool
        State of the link: Enabled (True), disabled (False).
    on_done : function()
        A function to call when the request has been completed.
    """

# Gives the FPGA number and register addresses for the STOP register (which
# disables outgoing traffic on a high-speed link) for each link direction.
# https://github.com/SpiNNakerManchester/spio/tree/master/designs/spinnaker_fpgas#spi-interface
REG_STOP_OFFSET = 0x5C
FPGA_LINK_STOP_REGISTERS = {
    Links.east: (0, 0x00000000 + REG_STOP_OFFSET),
    Links.south: (0, 0x00010000 + REG_STOP_OFFSET),
    Links.south_west: (1, 0x00000000 + REG_STOP_OFFSET),
    Links.west: (1, 0x00010000 + REG_STOP_OFFSET),
    Links.north: (2, 0x00000000 + REG_STOP_OFFSET),
    Links.north_east: (2, 0x00010000 + REG_STOP_OFFSET),
}


class AsyncBMPController(object):
    
    def __init__(self, hostname):
        self._bc = BMPController(hostname)
        
        self._stop = False
        
        # A lock which must be held when modifying the state of this object
        self._lock = threading.RLock()
        
        # An event fired whenever some new interaction with the BMP is
        # required.
        self._requests_pending = threading.Event()
        
        # A queue of power change states
        self._power_requests = deque()
        
        # A queue of link-enabled state changes
        self._link_requests = deque()
        
        self._thread = threading.Thread(
            target=self._run,
            name="<BMP control thread for {}>".format(hostname))
        self._thread.start()
    
    def __enter__(self):
        """When used as a context manager, make requests 'atomic'."""
        self._lock.acquire()
    
    def __exit__(self, type, value, traceback):
        self._lock.release()
    
    def set_power(self, board, state, on_done):
        """Set the power state of a single board.
        
        Parameters
        ----------
        board : int
            The board to control.
        state : bool
            True = on, False = off.
        on_done : function()
            Function to call when the command completes. May be called from
            another thread.
        """
        with self._lock:
            assert not self._stop
            
            # Enqueue the request
            self._power_requests.append(PowerRequest(state, board, on_done))
            self._requests_pending.set()
    
    def set_link_enable(self, board, link, enable, on_done):
        """Enable or disable a link.
        
        Parameters
        ----------
        board : int
            The board on which the link resides.
        link : :py:class:`rig.links.Links`
            The link to configure.
        enable : bool
            True = link enabled, False = link disabled.
        on_done : function()
            Function to call when the command completes. May be called from
            another thread.
        """
        with self._lock:
            assert not self._stop
            
            # Enqueue the request
            self._link_requests.append(LinkRequest(board, link, enable, on_done))
            self._requests_pending.set()
    
    def stop(self):
        """Stop the background thread, as soon as possible after completing all
        queued actions.
        """
        with self._lock:
            self._stop = True
            self._requests_pending.set()
    
    def join(self, *args, **kwargs):
        """Wait for the thread to actually stop."""
        self._thread.join(*args, **kwargs)
    
    def _run(self):
        """The background thread for interacting with the BMP.
        """
        try:
            while True:
                self._requests_pending.wait()
                
                # Priority 0: Power commands
                power_request = self._get_atomic_power_request()
                if power_request:
                    # Send the power command
                    try:
                        self._bc.set_power(state=power_request.state,
                                           board=power_request.board)
                    except IOError:
                        # Communication issue with the machine, log it but not
                        # much we can do for the end-user.
                        logging.exception("Failed to set board power.")
                    
                    # Alert all waiting threads
                    for on_done in power_request.on_done:
                        on_done()
                    
                    continue
                
                # Priority 1: Link enable/disable commands
                link_request = self._get_atomic_link_request()
                if link_request:
                    # Set the link state, as required
                    try:
                        fpga, addr \
                            = FPGA_LINK_STOP_REGISTERS[link_request.link]
                        self._bc.write_fpga_reg(fpga, addr,
                                                not link_request.enable,
                                                board=link_request.board)
                    except IOError:
                        # Communication issue with the machine, log it but not
                        # much we can do for the end-user.
                        logging.exception("Failed to set link state.")
                    
                    # Alert waiting thread
                    link_request.on_done()
                    
                    continue
                
                # If nothing left in the queues, clear the request flag and
                # break out of queue-processing loop.
                with self._lock:
                    if not self._power_requests and not self._link_requests:
                        self._requests_pending.clear()
                        
                        # If we've been told to stop, actually stop the thread now
                        if self._stop:
                            return
        except:  # pragma: no cover
            # If the thread crashes something has gone wrong with this program
            # (not the machine), setting _stop will cause set_power and
            # set_link_enable to fail, hopefully propogating news of this crash..
            with self._lock:
                self._stop = True
            raise
    
    def _get_atomic_power_request(self):
        """If any power requests are outstanding, return a (boards, state)
        tuple which combines as many of the requests at the head of the queue
        as possible.
        
        Returns
        -------
        :py:class:`.PowerRequest` or None
        """
        with self._lock:
            # Special case: no requests
            if not self._power_requests:
                return None
            
            # Otherwise, accumulate as many boards as possible
            state = self._power_requests[0].state
            boards = set()
            on_done = []
            while (self._power_requests and
                   self._power_requests[0].state == state):
                request = self._power_requests.popleft()
                boards.add(request.board)
                on_done.append(request.on_done)
            return PowerRequest(state, boards, on_done)
    
    def _get_atomic_link_request(self):
        """Pop the latest link state change request, if one exists."""
        with self._lock:
            if not self._link_requests:
                return None
            else:
                return self._link_requests.popleft()
