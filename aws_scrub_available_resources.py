#!/bin/env python
"""The program to traverse AWS account, removing unused resources."""

import boto3

VOLUME_FILTERS = [{
    'Name': 'status',
    'Values': ['available']
}]

def main():
    """The main program loop."""
    # iterate all the regions
    for aws_region in boto3.session.Session().get_available_regions('ec2'):
        aws = boto3.session.Session(region_name=aws_region)
        # delete all volumes that are not in-use
        for volume \
            in aws.resource('ec2').volumes.filter(Filters=VOLUME_FILTERS):
            print aws_region + "::" + volume.volume_id + \
                  ":" + volume.state + " volume deleted"
            volume.delete()
        # release all elastic IPs that are not attached
        for eip in [ \
                    eip for eip in aws.resource('ec2').vpc_addresses.all() \
                    if not eip.network_interface_id \
                   ]:
            print aws_region + "::" + eip.allocation_id + " eip released"
            eip.release()
        # delete all ELBs having no registered instances
        for elb in [ \
           elb for elb \
               in aws.client('elb'). \
               describe_load_balancers(). \
               get("LoadBalancerDescriptions", []) \
           if len(elb.get("Instances")) == 0 \
                   ]:
            print aws_region + "::" + \
                  elb.get("LoadBalancerName") + " elb deleted"
            aws.client('elb'). \
                delete_load_balancer( \
                LoadBalancerName=elb.get("LoadBalancerName"))

main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
