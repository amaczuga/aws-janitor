#!/bin/env python
# pylint: enable=wildcard-import, unused-wildcard-import
"""The program to traverse AWS account tagging VPC resources."""

import boto3
import sys

def delete_vpc_auto_scaling_groups(aws_session, vpc):
    """Delete all auto scaling groups related to a VPC"""
    subnet_ids = [subnet.subnet_id for subnet in vpc.subnets.all()]
    asg_client = aws_session.client('autoscaling')
    asg_list = asg_client.describe_auto_scaling_groups().get('AutoScalingGroups', [])
    for asg_name in [asg['AutoScalingGroupName'] for asg in asg_list if asg['VPCZoneIdentifier'] in subnet_ids]:
        asg_client.delete_auto_scaling_group(AutoScalingGroupName=asg_name, ForceDelete=True)
        print "%s::%s deleted." % (aws_session.region_name, asg_name)

def terminate_vpc_instances(aws_session, vpc):
    """Terminate all instances related to a VPC"""
    vpc_instances = vpc.instances.all()
    for instance in vpc_instances:
        instance.modify_attribute(DisableApiTermination={'Value':False})
        instance.terminate()
        print "%s::%s set for termination." % (aws_session.region_name, instance.id)
    for instance in vpc_instances:
        instance.wait_until_terminated()
        print "%s::%s terminated." % (aws_session.region_name, instance.id)

def delete_vpc_elbs(aws_session, vpc):
    """Delete all ELB's related to a VPC"""
    elb_client = aws_session.client('elb')
    elbs = elb_client.describe_load_balancers().get("LoadBalancerDescriptions", [])
    for elb_name in [elb['LoadBalancerName'] for elb in elbs if elb['VPCId'] == vpc.vpc_id]:
        elb_client.delete_load_balancer(LoadBalancerName=elb_name)
        print "%s::%s deleted." % (aws_session.region_name, elb_name)

def delete_vpc_route_tables(aws_session, vpc):
    """Delete all route tables related to a VPC"""
    not_main_filter = {
        'Name':'association.main',
        'Values':['false']
        }
    for rtbl in vpc.route_tables.all():
        for rtassoc in rtbl.associations.filter(Filters=[not_main_filter]):
            rtassoc.delete()
            print "%s::%s deleted." % (aws_session.region_name, rtassoc.route_table_association_id)
        if not rtbl.associations_attribute:
            rtbl.delete()
            print "%s::%s deleted." % (aws_session.region_name, rtbl.route_table_id)

def delete_vpc_subnets(aws_session, vpc):
    """Delete all subnets related to a VPC"""
    for subnet in vpc.subnets.all():
        subnet.delete()
        print "%s::%s deleted." % (aws_session.region_name, subnet.subnet_id)

def delete_vpc_security_groups(aws_session, vpc):
    """Delete all security groups related to a VPC"""
    for secgrp in vpc.security_groups.all():
        if not secgrp.group_name == 'default':
            secgrp.delete()
            print "%s::%s deleted." % (aws_session.region_name, secgrp.group_id)

def delete_vpc_gateways(aws_session, vpc):
    """Delete all internet gateways related to a VPC"""
    for igw in vpc.internet_gateways.all():
        igw.detach_from_vpc(VpcId=vpc.vpc_id)
        igw.delete()
        print "%s::%s deleted." % (aws_session.region_name, igw.internet_gateway_id)

def main():
    """The main program loop."""
    if len(sys.argv) > 1:
        for aws_region in boto3.session.Session().get_available_regions('ec2'):
            aws = boto3.session.Session(region_name=aws_region)
            for vpc in aws.resource('ec2').vpcs.all():
                if vpc.vpc_id == sys.argv[1]:
                    delete_vpc_auto_scaling_groups(aws, vpc)
                    terminate_vpc_instances(aws, vpc)
                    delete_vpc_elbs(aws, vpc)
                    delete_vpc_route_tables(aws, vpc)
                    delete_vpc_subnets(aws, vpc)
                    delete_vpc_security_groups(aws, vpc)
                    delete_vpc_gateways(aws, vpc)
                    vpc.delete()
                    print "%s::%s deleted." % (aws_region, vpc.vpc_id)

main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
