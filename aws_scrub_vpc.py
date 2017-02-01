#!/bin/env python
"""The program to traverse AWS account tagging VPC resources."""

import sys
import time
import botocore
import boto3

def delete_vpc_auto_scaling_groups(aws_session, vpc):
    """Delete all auto scaling groups related to a VPC"""
    subnet_ids = [subnet.subnet_id for subnet in vpc.subnets.all()]
    asg_client = aws_session.client('autoscaling')
    asg_list = asg_client.describe_auto_scaling_groups(). \
               get('AutoScalingGroups', [])
    for asg_name in [ \
         asg['AutoScalingGroupName'] for asg in asg_list \
         if asg['VPCZoneIdentifier'] in subnet_ids \
        ]:
        asg_client.delete_auto_scaling_group( \
            AutoScalingGroupName=asg_name, ForceDelete=True)
        print "%s::%s deleted." % (aws_session.region_name, asg_name)

def terminate_vpc_instances(aws_session, vpc):
    """Terminate all instances related to a VPC"""
    vpc_instances = vpc.instances.all()
    for instance in vpc_instances:
        instance.modify_attribute(DisableApiTermination={'Value':False})
        instance.terminate()
        print "%s::%s set for termination." % \
              (aws_session.region_name, instance.id)
    for instance in vpc_instances:
        instance.wait_until_terminated()
        print "%s::%s terminated." % (aws_session.region_name, instance.id)

def delete_vpc_elbs(aws_session, vpc):
    """Delete all ELB's related to a VPC"""
    elb_client = aws_session.client('elb')
    elbs = elb_client.describe_load_balancers(). \
           get("LoadBalancerDescriptions", [])
    for elb_name in [ \
          elb['LoadBalancerName'] for elb in elbs \
          if elb['VPCId'] == vpc.vpc_id \
                    ]:
        elb_client.delete_load_balancer(LoadBalancerName=elb_name)
        print "%s::%s deleted." % (aws_session.region_name, elb_name)

def delete_vpc_route_tables(aws_session, vpc):
    """Delete all route tables related to a VPC"""
    not_main_filter = [{
        'Name':'association.main',
        'Values':['false']
        }]
    for rtbl in vpc.route_tables.all():
        for rtassoc in rtbl.associations.filter(Filters=not_main_filter):
            rtassoc.delete()
            print "%s::%s deleted." % \
                  (aws_session.region_name, rtassoc.route_table_association_id)
        if not rtbl.associations_attribute:
            rtbl.delete()
            print "%s::%s deleted." % \
                  (aws_session.region_name, rtbl.route_table_id)

def delete_vpc_network_interfaces(aws_session, vpc):
    """Delete all network interfaces related to a VPC"""
    for eni in vpc.network_interfaces.all():
        eni.detach(Force=True)
        eni.delete()
        print "%s::%s deleted." % \
              (aws_session.region_name, eni.network_interface_id)

def delete_vpc_subnets(aws_session, vpc):
    """Delete all subnets related to a VPC"""
    for subnet in vpc.subnets.all():
        subnet.delete()
        print "%s::%s deleted." % (aws_session.region_name, subnet.subnet_id)

def refs_count(vpc_secgrps, secgrp):
    """Return number of secgrp references in vpc_secgrps"""
    refs = 0
    for grp in vpc_secgrps:
        for ip_perm in grp.ip_permissions + grp.ip_permissions_egress:
            for grp_pair in ip_perm.get('UserIdGroupPairs', []):
                if grp_pair.get('GroupId', '') == secgrp.group_id:
                    refs += 1
    return refs

def delete_vpc_security_groups(aws_session, vpc):
    """Delete all security groups related to a VPC"""
    vpc_secgrps = vpc.security_groups.all()
    group_refs = sorted([ \
                   (refs_count(vpc_secgrps, grp), grp) for grp in vpc_secgrps \
                        ])
    for secgrp in [grp[1] for grp in group_refs]:
        if not secgrp.group_name == 'default':
            secgrp.delete()
            print "%s::%s deleted." % (aws_session.region_name, secgrp.group_id)

def delete_vpc_gateways(aws_session, vpc):
    """Delete all gateways related to a VPC"""
    vpc_filter = [{
        'Name':'vpc-id',
        'Values':[vpc.vpc_id]
    }, {
        'Name':'state',
        'Values':['available', 'pending']
    }]
    ec2_client = aws_session.client('ec2')
    nats = ec2_client.describe_nat_gateways(Filters=vpc_filter). \
           get("NatGateways", [])
    for nat_id in [nat['NatGatewayId'] for nat in nats]:
        ec2_client.delete_nat_gateway(NatGatewayId=nat_id)
        print "%s::%s deleted." % (aws_session.region_name, nat_id)
    for igw in vpc.internet_gateways.all():
        igw.detach_from_vpc(VpcId=vpc.vpc_id)
        igw.delete()
        print "%s::%s deleted." % \
              (aws_session.region_name, igw.internet_gateway_id)

def delete_vpc(aws_session, vpc):
    """Delete the AWS VPC"""
    vpc.delete()
    print "%s::%s deleted." % (aws_session.region_name, vpc.vpc_id)

def main():
    """The main program loop."""
    if len(sys.argv) > 1:
        for aws_region in boto3.session.Session().get_available_regions('ec2'):
            aws = boto3.session.Session(region_name=aws_region)
            for vpc in aws.resource('ec2').vpcs.all():
                if vpc.vpc_id == sys.argv[1]:
                    while True:
                        try:
                            delete_vpc_auto_scaling_groups(aws, vpc)
                            terminate_vpc_instances(aws, vpc)
                            delete_vpc_elbs(aws, vpc)
                            delete_vpc_route_tables(aws, vpc)
                            delete_vpc_gateways(aws, vpc)
                            delete_vpc_network_interfaces(aws, vpc)
                            delete_vpc_subnets(aws, vpc)
                            delete_vpc_security_groups(aws, vpc)
                            delete_vpc(aws, vpc)
                            break
                        except Exception:
                            time.sleep(10)

main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
