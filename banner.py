#!/usr/bin/env python
import os
import sys

from cloudinary.api import delete_resources_by_tag, resources_by_tag
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
from cloudinary import CloudinaryImage

# config
os.chdir(os.path.join(os.path.dirname(sys.argv[0]), '.'))
if os.path.exists('settings.py'):
    exec(open('settings.py').read())

DEFAULT_TAG = "alert_basic"

def dump_response(response):
    print("Upload response:")
    for key in sorted(response.keys()):
        print("  %s: %s" % (key, response[key]))


def upload_files():
    print("--- Upload a local file")
    response = upload("alert_visual.png", tags=DEFAULT_TAG)
    return response

def determine_overlay(event):
    ''' Determines appropriate overlay on the Cloudinary server '''

    return {
        'Tornado Warning': 'Overlays:Tornado',
        'Severe Thunderstorm Warning': 'Overlays:Severe',
        'Flash Flood Warning': 'Overlays:Flash'
    }.get(event, 'Overlays:Default')

def extract_url(src):
    image_url = src.split('"')[1]
    return image_url

def upload_and_no_transform():
    ''' Uploads file to cloudinary and returns image URL '''
    response = upload_files()
    image_url = cloudinary_url(response['public_id'], format=response['format'])
    print(image_url[0])
    return image_url[0]

def upload_and_transform(event):
    ''' 
    Uploads file to cloudinary, selects appropriate overlay based on the
    alert type, and returns the image URL
    '''
    response = upload_files()
    
    image_src = CloudinaryImage(f"{response['public_id']}.{response['format']}").image(
        transformation=[ {'overlay': determine_overlay(event)} ])

    image_url = extract_url(image_src)
    print(image_url)
    return image_url

def upload_and_multiple_transform():
    response = upload_files()
    image_src = CloudinaryImage(f"{response['public_id']}.{response['format']}").image(
        transformation=[
        {'overlay': 'Overlay:default'},
        {'color': "black", 'overlay': {
            'font_family': "Arial", 
            'font_size': 100, 
            'font_weight': "bold",
            'text': "Hi",
            }
        },
        {'flags': "layer_apply", 'gravity': "north_west", 'x': 80, 'y': 45}
        ])
    
    image_url = extract_url(image_src)
    print(image_url) 


def cleanup():
    response = resources_by_tag(DEFAULT_TAG)
    resources = response.get('resources', [])
    if not resources:
        print("No images found")
        return
    print("Deleting {0:d} images...".format(len(resources)))
    delete_resources_by_tag(DEFAULT_TAG)
    print("Done!")


if len(sys.argv) > 1:
    if sys.argv[1] == 'upload':
        upload_files()
    if sys.argv[1] == 'cleanup':
        cleanup()
else:
    print("--- Uploading files and then cleaning up")
    print("    you can only choose one instead by passing 'upload' or 'cleanup' as an argument")
    print("")
    #upload_and_transform('Tornado Warning')
    #cleanup()