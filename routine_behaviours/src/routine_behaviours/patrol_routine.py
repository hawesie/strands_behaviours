#!/usr/bin/env python

import rospy

from strands_executive_msgs import task_utils
from strands_executive_msgs.msg import Task
from strands_navigation_msgs.msg import TopologicalMap
from mongodb_store_msgs.msg import StringList
from mongodb_store.message_store import MessageStoreProxy

from datetime import time, date
from dateutil.tz import tzlocal

from routine_behaviours.robot_routine import RobotRoutine

import random


def create_patrol_task(waypoint_name):
    return Task(start_node_id=waypoint_name, max_duration=rospy.Duration(30))


class PatrolRoutine(RobotRoutine):
    """Wraps up all the routine stuff"""
    def __init__(self, daily_start, daily_end, tour_duration_estimate=None):
        # super(PatrolRoutine, self).__init__(daily_start, daily_end)        
        RobotRoutine.__init__(self, daily_start, daily_end, idle_duration=rospy.Duration(5))
        self.node_names = []
        self.tour_duration_estimate = tour_duration_estimate
        rospy.Subscriber('topological_map', TopologicalMap, self.map_callback)

    def map_callback(self, msg):        
        print 'got map: %s' % len(msg.nodes)
        self.node_names = [node.name for node in msg.nodes]
        
    def get_nodes(self):
        while len(self.node_names) == 0:
            print 'no nodes'
            rospy.sleep(1)
        return self.node_names


    def create_routine(self):
        
        # these could be useful
        node_names_inc_charging = self.get_nodes()         
        node_names = [n for n in node_names_inc_charging if n != 'ChargingPoint']

        # the tour_duration_estimate tells us how big the time window for a single tour should be
        # if this is underestimated then scheduling will fail
        # if overestimated, this is no big deal but the robot will go idle more
        if not self.tour_duration_estimate:
            single_node_estimate = 60
            self.tour_duration_estimate=rospy.Duration(single_node_estimate * len(node_names))


        localtz = tzlocal()

        patrol_at = node_names
        patrol_tasks = [ create_patrol_task(n) for n in patrol_at]

        # ADD TASKS TO ROUTINE

        self.routine.repeat_every_mins(patrol_tasks, mins=int(self.tour_duration_estimate.to_sec()/60), times=1)

        # self.runner.add_day_off('Saturday')
        # self.runner.add_day_off('Sunday')        
        # self.runner.add_date_off(date(2014, 05, 26))

        # NIGHT TASKS
        # this is how you add something for when the robot is charging, but these tasks aren't allowed a location
        # clear_datacentre_task = create_datacentre_task(['heads','metric_map_data','rosout_agg','robot_pose','task_events','scheduling_problems','ws_observations','monitored_nav_events'])
        # self.add_night_task(clear_datacentre_task)


        # pass the routine tasks on to the runner which handles the daily instantiation of actual tasks
        self.start_routine()        

    def on_idle(self):
        """
            Called when the routine is idle. Default is to trigger travel to the charging. As idleness is determined by the current schedule, if this call doesn't utlimately cause a task schedule to be generated this will be called repeatedly.
        """
        rospy.loginfo('Idle for too long, generating a random waypoint task')
        self.add_tasks([create_patrol_task(random.choice(self.node_names))])
    
