#!/usr/bin/env python
'''
map display module
Andrew Tridgell
June 2012
'''

import sys, os, cv, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))
import mp_slipmap, mp_util

mpstate = None

class module_state(object):
    def __init__(self):
        self.lat = None
        self.lon = None
        self.heading = 0
        self.wp_change_time = 0
        self.fence_change_time = 0
        self.have_simstate = False
        self.have_blueplane = False

def name():
    '''return module name'''
    return "map"

def description():
    '''return module description'''
    return "map display"

def init(_mpstate):
    '''initialise module'''
    global mpstate
    mpstate = _mpstate
    mpstate.map_state = module_state()
    mpstate.map = mp_slipmap.MPSlipMap(service='GoogleSat', elevation=True, title='Map')

    # setup a plane icon
    icon = mpstate.map.icon('planetracker.png')
    mpstate.map.add_object(mp_slipmap.SlipIcon('plane', (0,0), icon, layer=3, rotation=0,
                                               follow=True,
                                               trail=mp_slipmap.SlipTrail()))

def unload():
    '''unload module'''
    mpstate.map = None

def create_blueplane():
    '''add the blue plane to the map'''
    if mpstate.map_state.have_blueplane:
        return
    mpstate.map_state.have_blueplane = True
    icon = mpstate.map.icon('blueplane.png')
    mpstate.map.add_object(mp_slipmap.SlipIcon('blueplane', (0,0), icon, layer=3, rotation=0,
                                               trail=mp_slipmap.SlipTrail()))

def mavlink_packet(m):
    '''handle an incoming mavlink packet'''
    state = mpstate.map_state

    if m.get_type() == "SIMSTATE":
        if not mpstate.map_state.have_simstate:
            mpstate.map_state.have_simstate  = True
            create_blueplane()
        mpstate.map.set_position('blueplane', (m.lat, m.lng), rotation=math.degrees(m.yaw))

    if m.get_type() == "GPS_RAW_INT" and not mpstate.map_state.have_simstate:
        (lat, lon) = (m.lat*1.0e-7, m.lon*1.0e-7)
        if state.lat is not None and (mpstate.map_state.have_blueplane or
                                      mp_util.gps_distance(lat, lon, state.lat, state.lon) > 10):
            create_blueplane()
            mpstate.map.set_position('blueplane', (lat, lon), rotation=m.cog*0.01)

    if m.get_type() == 'GLOBAL_POSITION_INT':
        (state.lat, state.lon, state.heading) = (m.lat*1.0e-7, m.lon*1.0e-7, m.hdg*0.01)
    else:
        return

    mpstate.map.set_position('plane', (state.lat, state.lon), rotation=state.heading)

    # if the waypoints have changed, redisplay
    if state.wp_change_time != mpstate.status.wploader.last_change:
        state.wp_change_time = mpstate.status.wploader.last_change
        points = mpstate.status.wploader.polygon()
        if len(points) > 1:
            mpstate.map.add_object(mp_slipmap.SlipPolygon('mission', points, layer=1, linewidth=2, colour=(255,255,255)))

    # if the fence has changed, redisplay
    if state.fence_change_time != mpstate.status.fenceloader.last_change:
        state.fence_change_time = mpstate.status.fenceloader.last_change
        points = mpstate.status.fenceloader.polygon()
        if len(points) > 1:
            mpstate.map.add_object(mp_slipmap.SlipPolygon('fence', points, layer=1, linewidth=2, colour=(0,255,0)))

    # check for any events from the map
    mpstate.map.check_events()
    