#!/bin/env python
# pylint: enable=wildcard-import, unused-wildcard-import
"""The program to traverse AWS account looking for VPCs."""

import boto3
import json

def format_tags(tags, subset_tags):
    """Print tag subset."""
    tagstring = ""
    if tags:
        for subset_key in subset_tags:
            if any(subset_key in tag["Key"] for tag in tags):
                tag_value = (tag for tag in tags if tag["Key"] == subset_key).next()["Value"]
                tagstring += "\t%s:%s" % (subset_key, tag_value)
    return tagstring

def main():
    """The main program loop."""
    with open('config.json', 'r') as config_file:
        intel_tags = json.load(config_file).get("PATTERN_TAGS", {})

    for aws_region in boto3.session.Session().get_available_regions('ec2'):
        aws = boto3.session.Session(region_name=aws_region)
        for vpc in aws.resource('ec2').vpcs.all():
            instance_count = sum(1 for e in vpc.instances.all())
            vpc_desc = "%s::%s::%d " % (aws_region, vpc.vpc_id, instance_count)
            print vpc_desc + format_tags(vpc.tags, intel_tags)

main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
