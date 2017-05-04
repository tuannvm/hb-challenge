#!/usr/bin/env python
# coding=utf-8
import docker
import os
from tabulate import tabulate  # library which help print clean table
import argparse
import requests
import json


def get_image_digest(image_name, tag):
    """
    Help get remote image digest from dockerhub
    :param image_name: image_name or repo_name to check 
    :param tag: image_tag (latest, develop, alpine...)
    :return: return string
    """
    # append "library/" prefix if image is official
    if "/" not in image_name:
        image_name = "library/" + image_name

    # get access_token
    url = "https://auth.docker.io/token"
    payloads = {"service": "registry.docker.io", "scope": "repository:" + image_name + ":pull"}
    r = requests.get(url, params=payloads)
    access_token = json.loads(r.text)["token"]

    # get image digest using access_token above
    url = "https://index.docker.io/v2/" + image_name + "/manifests/" + tag
    headers = {
               "Host": "index.docker.io",
               "Authorization": "Bearer " + access_token,
               "Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    r = requests.get(url, headers=headers)

    return r.headers['Docker-Content-Digest']


def pydock(**kwargs):
    """
    pydock help you know which containers run on deprecated image
    :return:
    """
    # Initialize client
    try:
        socket = kwargs["socket"]
        local = kwargs["local"]
        tls = kwargs["tls"]
        ca_file = kwargs["ca_file"]
        client_cert = kwargs["client_cert"]
        client_key = kwargs["client_key"]

    except KeyError as e:
        print e

    try:
        if socket is not None:  # check if remote host is defined
            if not tls:  # check if tls is enabled
                client = docker.DockerClient(base_url=socket, version="auto")  # connect without tls
            else:
                tls_config = docker.tls.TLSConfig(  # define certs
                    ca_cert=ca_file,
                    client_cert=(client_cert, client_key)
                )
                client = docker.DockerClient(base_url=socket, version="auto", tls=tls_config)  # connect with tls
        else:
            client = docker.from_env(version="auto")  # connect to local daemon

        # pre-define lists
        containers_list = []
        results = []

        # get all running containers
        containers = client.containers.list()
        for container in containers:
            # parse data, save container"s info to a list
            containers_list.append({"name": container.attrs["Config"]["Image"],  # container name + tag
                                    "id": container.short_id,  # container short id
                                    "image_id": container.attrs["Image"],  # image id
                                    "update": True,
                                    "remote_update": True})  # default to true, up-to-date

        for container in containers_list:
            # append latest tag if container was started with image-only parameter
            if ":" not in container["name"]:
                container["name"] += ":latest"

            # get image object
            image = client.images.get(container["name"])

            # split the value <image_name>:<tag>
            image_name = container["name"].split(":")[0]
            tag = container["name"].split(":")[1]

            # if container"s image id and server image id are different, switch value to False
            if container["image_id"] != image.id:
                container["update"] = False

            if not local:  # if local check is disabled (default)
                image_digest = get_image_digest(image_name, tag)  # get image digest
                local_image_digest = str(image.attrs['RepoDigests'][0]).split("@")[1]

                # compare 2 digests
                if local_image_digest != image_digest:
                    container["remote_update"] = False

                # prepare results to print
                results.append([container["id"], image_name, tag, container["update"], container["remote_update"]])
                headers = ["CONTAINER ID", "IMAGE", "TAG", "LOCAL UP TO DATE?", "REMOTE UP TO DATE?"]
            else:
                results.append([container["id"], image_name, tag, container["update"]])
                headers = ["CONTAINER ID", "IMAGE", "TAG", "LOCAL UP TO DATE?"]

        # print table
        print tabulate(results, headers=headers)

    # check if can not connect to Docker API
    except docker.errors.DockerException as e:
        print e
        print "Could not connect to Docker API, please make sure Docker service is started!"
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-H", dest="socket",
                        help="Define remote Docker host. E.g: tcp://<host>:<port>")

    parser.add_argument("--local", action="store_true",
                        dest="local",
                        help="local check only")

    parser.add_argument("--tlsverify", action="store_true",
                        dest="tls",
                        help="enable client TLS verification")

    parser.add_argument("--tlscacert", dest="ca_file",
                        help="Set CA pem file")

    parser.add_argument("--tlscert",
                        dest="client_cert",
                        help="Set client cert file")

    parser.add_argument("--tlskey", dest="client_key",
                        help="set client private key")

    parser.add_argument("--version", action="version", version="pydock 1.0.0")

    results = parser.parse_args()

    try:
        if results.tls:  # further check if additional argument are needed in case tls is enabled
            assert results.ca_file, "--tlscacert needs to be defined if --tlsverify was declared"
            assert results.client_cert, "--tlscert needs to be defined if --tlsverify was declared"
            assert results.client_key, "--tlskey needs to be defined if --tlsverify was declared"
    except AssertionError as e:
        print e
        exit(1)

    # get ENV to use in docker container
    pydock(socket=results.socket,
           tls=results.tls or bool(os.environ.get("TLS")),
           local=results.local or bool(os.environ.get("LOCAL")),
           ca_file=results.ca_file or os.environ.get("CA_FILE"),
           client_cert=results.client_cert or os.environ.get("CLIENT_CERT"),
           client_key=results.client_key or os.environ.get("CLIENT_KEY"))
