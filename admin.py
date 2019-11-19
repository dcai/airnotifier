#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click
import sys
import logging


@click.group(name="admin")
def cli():
    pass


@cli.command(name="adduser")
@click.option("--email", help="email")
@click.option("--password", help="org id")
@click.option("--org", help="org id")
def cmd_add_user(email, password, org):
    logging.info("add user")


@cli.command(name="chanageorg")
@click.option("--email", help="email")
@click.option("--org", help="org id")
def cmd_change_org(user, org):
    pass


@cli.command(name="changepassword")
@click.option("--email", help="email")
@click.option("--password", help="password")
def cmd_chanage_password(user, password):
    pass


if __name__ == "__main__":
    cli()
