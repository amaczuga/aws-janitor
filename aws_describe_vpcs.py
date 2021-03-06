#!/bin/env python
"""A program to traverse AWS account describing all VPCs."""

import json
from datetime import datetime
from jmespath import search
import argparse
import requests
import pytz
import boto3

PRICING_URL = \
    'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json'

REGIONS = {
    'US East (N. Virginia)': 'us-east-1',
    'US East (Ohio)': 'us-east-2',
    'US West (N. California)': 'us-west-1',
    'US West (Oregon)': 'us-west-2',
    'Canada (Central)': 'ca-central-1',
    'Asia Pacific (Mumbai)': 'ap-south-1',
    'Asia Pacific (Seoul)': 'ap-northeast-2',
    'Asia Pacific (Singapore)': 'ap-southeast-1',
    'Asia Pacific (Sydney)': 'ap-southeast-2',
    'Asia Pacific (Tokyo)': 'ap-northeast-1',
    'EU (Frankfurt)': 'eu-central-1',
    'EU (Ireland)': 'eu-west-1',
    'EU (London)': 'eu-west-2',
    'South America (Sao Paulo)': 'sa-east-1'
    }

SKU_FILTER = '[? \
    productFamily == `Compute Instance` && \
    attributes.operatingSystem == `Linux` && \
    attributes.tenancy == `Shared` \
    ].sku'

PRICE_FILTER = '*.priceDimensions.*[].pricePerUnit.USD | [0]'

FORMATS = {
    'txt': '%-12s %s %3d %4d $%6.2f %-20.20s %-8s %-4s %-20.20s %-5s',
    'csv': '%s;%s;%d;%d;$%.2f;%s;%s;%s;%s;%s'
    }

def get_ec2_prices(pricing_url):
    """Download and parse AWS EC2 compute pricing plans"""
    prices = {}
    pricing = json.loads(requests.get(pricing_url).content)
    for sku in search(SKU_FILTER, pricing['products'].values()):
        if pricing['terms']['OnDemand'].get(sku):
            inst_location = pricing['products'][sku]['attributes']['location']
            inst_type = pricing['products'][sku]['attributes']['instanceType']
            inst_price = search(PRICE_FILTER, pricing['terms']['OnDemand'][sku])
            if inst_location in REGIONS:
                if not REGIONS[inst_location] in prices:
                    prices[REGIONS[inst_location]] = {}
                prices[REGIONS[inst_location]][inst_type] = float(inst_price)
    return prices

def format_tags(tags, subset_tags):
    """Print tag subset."""
    tagstring = ""
    if tags:
        for subset_key in subset_tags:
            if any(subset_key in tag["Key"] for tag in tags):
                tag_value = (
                    tag for tag in tags if tag["Key"] == subset_key
                    ).next()["Value"]
                tagstring += "\t%s:%s" % (subset_key, tag_value)
    return tagstring

def tags2dict(aws_tags):
    """Convert AWS-style tags to a dict type tags."""
    tag_dict = {}
    if aws_tags:
        for awstag in aws_tags:
            tag_dict[awstag["Key"]] = awstag["Value"]
    return tag_dict

def main():
    """The main program loop."""
    argparser = argparse.ArgumentParser(description='Print out VPC data')
    argparser.add_argument('--format', choices=['txt', 'csv'], default='txt')
    args = argparser.parse_args()
    row_format = FORMATS.get(args.format)
    ec2_prices = get_ec2_prices(PRICING_URL)

    for aws_region in boto3.session.Session().get_available_regions('ec2'):
        aws = boto3.session.Session(region_name=aws_region)
        for vpc in aws.resource('ec2').vpcs.all():
            vpc_price = 0
            instances = vpc.instances.all()
            for inst in instances:
                vpc_price += ec2_prices[aws_region][inst.instance_type] * 24
            inst_cnt = sum(1 for e in instances)
            now = datetime.now().replace(tzinfo=pytz.utc)
            inst_start = min([inst.launch_time for inst in instances] or [now])
            vpc_age = (now - inst_start).days + 1
            vpc_desc = row_format % (aws_region, vpc.vpc_id, inst_cnt,
                                     vpc_age, vpc_price,
                                     tags2dict(vpc.tags).get("Name"),
                                     tags2dict(vpc.tags).get("Owner"),
                                     tags2dict(vpc.tags).get("Environment"),
                                     tags2dict(vpc.tags).get("Project"),
                                     tags2dict(vpc.tags).get("IAP")
                                    )
            print vpc_desc

main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
