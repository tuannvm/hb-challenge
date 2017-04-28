#!/usr/bin/env python
# coding=utf-8
import docker
import os
from tabulate import tabulate  # library which help print clean table
import argparse


def pydock(**kwargs):
    """
    pydock help you know which containers run on deprecated image    
    :return: 
    """
    # Initialize client
    try:
        socket = kwargs['socket']
        tls = kwargs['tls']
        ca_file = kwargs['ca_file']
        client_cert = kwargs['client_cert']
        client_key = kwargs['client_key']

    except KeyError as e:
        print e

    try:
        if socket is not None:  # check if remote host is defined
            if not tls:  # check if tls is enabled
                client = docker.DockerClient(base_url=socket, version='auto')  # connect without tls
            else:
                tls_config = docker.tls.TLSConfig(  # define certs
                    ca_cert=ca_file,
                    client_cert=(client_cert, client_key)
                )
                client = docker.DockerClient(base_url=socket, version='auto', tls=tls_config)  # connect with tls
        else:
            client = docker.from_env(version='auto')  # connect to local daemon

        # pre-define lists
        containers_list = []
        results = []

        # get all running containers
        containers = client.containers.list()
        for container in containers:
            # parse data, save container's info to a list
            containers_list.append({"name": container.attrs['Config']['Image'],  # container name + tag
                                    "id": container.short_id,  # container short id
                                    "image_id": container.attrs['Image'],  # image id
                                    "update": True})  # default to true, up-to-date

        for container in containers_list:
            # append latest tag if container was started with image-only parameter
            if ":" not in container["name"]:
                container["name"] += ":latest"

            # get image object
            image = client.images.get(container["name"])

            # if container's image id and server image id are different, switch value to False
            if container["image_id"] != image.id:
                container["update"] = False

            # prepare value to print result as a table
            image_name = container["name"].split(":")[0]
            tag = container["name"].split(":")[1]
            results.append([container["id"], image_name, tag, container["update"]])

        # print table
        print tabulate(results, headers=['CONTAINER ID', 'IMAGE', 'TAG', 'UP TO DATE?'])

    except docker.errors.DockerException as e:
        print e
        print "Could not connect to Docker API, please make sure Docker service is started!"
        exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-H', dest='socket',
                        help='Define remote Docker host. E.g: tcp://<host>:<port>')

    parser.add_argument('--tlsverify', action='store_true',
                        dest='tls',
                        help='enable client TLS verification')

    parser.add_argument('--tlscacert', dest='ca_file',
                        help='Set CA pem file')

    parser.add_argument('--tlscert',
                        dest='client_cert',
                        help='Set client cert file')

    parser.add_argument('--tlskey', dest='client_key',
                        help='set client private key')

    parser.add_argument('--version', action='version', version='pydock 1.0.0')

    results = parser.parse_args()

    try:
        if results.tls:  # further check if additional argument are needed in case tls is enabled
            assert (results.ca_file), '--tlscacert needs to be defined if --tlsverify was declared'
            assert (results.client_cert), '--tlscert needs to be defined if --tlsverify was declared'
            assert (results.client_key), '--tlskey needs to be defined if --tlsverify was declared'
    except AssertionError as e:
        print e
        exit(1)

    # get ENV to use in docker container
    pydock(socket=results.socket,
           tls=results.tls or bool(os.environ.get('TLS')),
           ca_file=results.ca_file or os.environ.get('CA_FILE'),
           client_cert=results.client_cert or os.environ.get('CLIENT_CERT'),
           client_key=results.client_key or os.environ.get('CLIENT_KEY'))
