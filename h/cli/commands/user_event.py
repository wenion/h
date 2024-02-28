# pylint: disable=redefined-outer-name
import click

from h import models_redis


@click.group("event")
def user_event():
    """Manage user event."""


@user_event.command()
@click.argument("username")
@click.option("--authority")
@click.pass_context
def length(ctx, username, authority):
    """
    Show total events for user.

    You must specify the username of a user which you wish to give
    administrative privileges.
    """
    request = ctx.obj["bootstrap"]()

    if not authority:
        authority = request.default_authority

    userid = "acct:"+ username + "@" + authority

    result = models_redis.fetch_all_user_event(userid, "timestamp")
    request.tm.commit()

    click.echo(f"{username} has {result['total']} records", err=True)


@user_event.command()
@click.argument("username")
@click.option("--authority")
@click.option("--type")
@click.pass_context
def delete(ctx, username, authority, type):
    """
    Delete a user with all their group memberships and annotations.

    You must specify the username of a user to delete.
    """
    request = ctx.obj["bootstrap"]()

    if not authority:
        authority = request.default_authority

    if not type:
        type = 'all'

    userid = "acct:"+ username + "@" + authority

    result = models_redis.del_user_event(userid, type)
    request.tm.commit()

    click.echo(f"{result['total']} records[TYPE:{type}] of User {username} have been deleted.", err=True)
