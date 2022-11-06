# <div align="center">Alert Invites Example <br /> <a href="https://invite-manager.net"><img src="https://invite-manager.net/images/logo.png" height=25 weight=25 /></a></div>

<p align="center">
  <a href="https://invite-manager.net/invite">Invite Me</a> |
  <a href="https://invite-manager.net/premium">Support Us</a>
</p>

# Features

- [InviteManager Webhook Feature](https://docs.invite-manager.net/documentation/alert-invites#webhooks)
  - Give a role when user reach _n_ invites
- Easy Management
  - Add, remove & list reward roles

# How does it work?

This bot mainly uses [Alert Invites](https://docs.invite-manager.net/documentation/alert-invites) feature of the [InviteManager bot](https://invite-manager.net/) to work.

So before you start this bot, consider the following requirements:

- Alert Invites Webhook needs to be set to the webhook url of this bot.

This is necessary because that is how this bot knows when a new alert invite has been triggered,
this can be set by doing the following command: `/alert-invites webhook url http://my-webhook.net`

You can also test if this bot is receiving the requests correctly by doing `/alert-invites webhook test`, after doing this command you should receive a new alert-invite in this bot (if works).

- All reward roles configured in this bot have to be configured as [alert invites](https://docs.invite-manager.net/documentation/alert-invites) in the InviteManager bot.

This is necessary because the InviteManager only sends alert-invites that are configured.
e.g. if you set a reward role at **10 invites** in this bot, but in the InviteManager you only have **15 invites** set as alert-invite, InviteManager will not request your webhook url when someone gets 10 invites in your server.

# Installation

The installation steps are as follows:

- Make sure to get [Python 3.8](https://www.python.org/downloads/) or higher
- Install dependencies, doing, `pip install -U -r requirements.txt`
- Create the database in PostgreSQL.
  You will need [PostgreSQL 9.1](https://www.postgresql.org/download/) or higher,
  type the following in the `psql` tool:

```sql
CREATE ROLE InviteManager WITH LOGIN PASSWORD 'your-password'; -- Creating a role with a password
CREATE DATABASE AlertInvitesEx OWNER InviteManager; -- Creating the database, and give the role above ownership
```

## Setup Configuration

For the configuration rename the file `configs.py.example` -> `configs.py`, and then fill in all the requested data in the file `configs.py`.

## Running

Now for the best part, running, for that we have to start by setting up the database, i.e. creating all the tables needed for the bot to work.
To do so, do the following commands:

```sh
C:\Windows> py . db init

Linux@InvMan:~$ python3 . db init
```

Now with all the database creation done, we can start this bot, for this do the following commands:

```sh
C:\Windows> py .

Linux@InvMan:~$ python3 .
```

And... that's it. Now you should be running the bot.

### Syncing Slash Commands

This bot only uses slash commands, this means that to **appear the commands in all guilds** those commands will have to be synchronized with the discord API, to do the (global, i.e. all guilds) synchronization just do the following command: `@BotPing sync`
