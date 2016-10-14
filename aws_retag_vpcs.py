#!/bin/env python
# pylint: enable=wildcard-import, unused-wildcard-import
"""The program to traverse AWS account tagging VPC resources."""

import boto3
import json
import re

def valid_tags(tags, pattern_tags):
    """Regex-based tags validator, Boolean."""
    valid = True
    if tags:
        for pattern_key in pattern_tags:
            if any(pattern_key in tag["Key"] for tag in tags):
                tag_value = (tag for tag in tags if tag["Key"] == pattern_key).next()["Value"]
                if not re.match(pattern_tags[pattern_key], tag_value):
                    valid = valid and False
            else:
                valid = valid and False
    return valid

def main():
    """The main program loop."""
    with open('config.json', 'r') as config_file:
        intel_tags = json.load(config_file).get("PATTERN_TAGS", {})

    for aws_region in boto3.session.Session().get_available_regions('ec2'):
        aws = boto3.session.Session(region_name=aws_region)
        for vpc in aws.resource('ec2').vpcs.all():
            instance_count = sum(1 for e in vpc.instances.all())
            if valid_tags(vpc.tags, intel_tags) and instance_count > 0:
                vpc_desc = "%s::%s::%d " % (aws_region, vpc.vpc_id, instance_count)
                print vpc_desc + "instances tagged."
                selected_tags = [tag for tag in vpc.tags if tag["Key"] in intel_tags.keys()]
                vpc_inst = [inst.id for inst in vpc.instances.all()]
                aws.client('ec2').create_tags(Resources=vpc_inst, Tags=selected_tags)

main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
