# pylint: disable=redefined-outer-name
import click

from h.models_redis import UserEvent


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

    total = UserEvent.find(UserEvent.userid == userid).count()
    request.tm.commit()

    click.echo(f"{username} has {total} records", err=True)


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

    if type == 'all':
        query = UserEvent.find(UserEvent.userid == userid)
    else:
        query = UserEvent.find(
            (UserEvent.userid == userid) &
            (UserEvent.event_type == type)
        )
    total = query.count()
    result = query.all()

    for item in result:
        UserEvent.delete(item.pk)

    request.tm.commit()

    click.echo(f"{total} records[TYPE:{type}] of User {username} have been deleted.", err=True)
