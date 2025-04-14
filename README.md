# Simple Applications Bot (SAB)

## Overview
SAB or Simple Applications Bot is a Discord bot designed in Python to streamline and manage application processes within Discord servers. It allows server administrators to create custom application forms, manage submissions, and review applications that comes with a intuitive web dashboard.

At it's current iteration each running instance of the bot only supports managing one guild (or server). This likely what the  next major feature update would be.

## Features
- **Application Panels**: Create application panels with select menus for different positions to make it extremely intuitive for the end user!
- **High customisability**: Configure pretty much every aspect of the bot!
- **Web Dashboard**: Bot comes with a powerful yet simple internal dashboard to manage the various aspects of the bot!
- **Thread Creation**: Automatically create threads to discuss applicants with your staff members!

For support:
[![Discord](https://img.shields.io/discord/1352548670532227072?label=discord&amp;color=7289DA&amp;style=for-the-badge)](https://discord.gg/EBM9MKkD7F)

## Installation

## Bot setup

1. Clone the repository
```bash
git clone https://github.com/Cirkutry/application-bot.git
cd application-bot
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables by copying the example environment file to a file named `.env` and filling in your details.
    - For Linux:
    ```bash
    cp .env.example .env
    ```
    - For Windows:
    ```bash
    copy .env.example .env
    ```
4. Start the bot
```bash
python main.py
```
The bot will start and connect to your Discord server. You should see output confirming:
- Bot connection to Discord
- Web dashboard availability
- Registration of bot views if any

## `.env` file setup 

Required environment variables:
- `TOKEN`: Discord bot's token - (See #discord-developer-portal-setup for more info)

- `SERVER_ID`: ID of your Discord server - This will require `Developer Mode` enabled under the `Advanced` section in Discord settings, after which you can right-click your server and click `Copy Server ID` and paste it's value in this variable.

- `WEB_HOST`: Host IP for the web dashboard - Set this to localhost for testing locally or set it to your public facing IP of your host (without `http://` or `https://`)

- `WEB_PORT`: Port for the web dashboard - Make sure your firewall has this port open if you're accessing the dashboard from outside the host IP.

- `OAUTH_CLIENT_ID`: Discord OAuth client ID - (See #discord-developer-portal-setup for more info)

- `OAUTH_CLIENT_SECRET`: Discord OAuth client secret - (See #discord-developer-portal-setup for more info)

- `OAUTH_REDIRECT_URI`: Discord OAuth redirect URI - (See #discord-developer-portal-setup for more info)

## Discord Developer Portal setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)

2. Create an application

	1. Click the `New Application` button
	2. Give your application a name, accept the terms of service and click `Create`

	![Screenshot](https://raw.githubusercontent.com/discord-tickets/docs/refs/heads/main/docs/img/discord-application-1.png)
3. In the page that appears you can add a logo, description, or links to your terms of service and privacy policy if you wish to, and then click `Save Changes`.

	![Screenshot](https://raw.githubusercontent.com/discord-tickets/docs/refs/heads/main/docs/img/discord-application-2.png)

4. Go to the `OAuth2` page and click `Reset Secret`, then `Yes, do it!`.
	**Copy the new secret and set it as your `OAUTH_CLIENT_SECRET` environment variable.**

	![Screenshot](https://raw.githubusercontent.com/discord-tickets/docs/refs/heads/main/docs/img/discord-application-3.png)
5. Click `Add Redirect` and enter the `WEB_HOST` followed by `WEB_PORT`, preceeded by either `http://` or `https://` environment variable, followed by `/auth/callback`.
	Then click `Save Changes`.

> [!IMPORTANT]
> Examples:
> - `http://12.345.67.89:8080/auth/callback`
> - `http://localhost:8080/auth/callback`
> - `https://example.com/auth/callback`

![Screenshot](https://raw.githubusercontent.com/discord-tickets/docs/refs/heads/main/docs/img/discord-application-4.png)

6. Also in the same page copy the `CLIENT ID` by hitting the `COPY` button and set it as your `OAUTH_CLIENT_ID` environment variable.
7. Navigate to the `Bot` page

	1. Click `View Token`, then **copy the token and set it as your `TOKEN` environment variable.**
	2. We highly recommend disabling the "Public Bot" option to prevent other people from adding your bot to their servers. Before you can do so, you will need to go to to the `Installation` page and set `Install Link` to `None`. After saving changes, return to the `Bot` page and disable the "Public Bot" option.

	![Screenshot](https://raw.githubusercontent.com/discord-tickets/docs/refs/heads/main/docs/img/discord-application-5.png)

	3. **Enable the `presence`, `server members` and `message content` intents.**

	![Screenshot](https://raw.githubusercontent.com/discord-tickets/docs/refs/heads/main/docs/img/discord-application-6.png)

To add the bot to your server, use the below URL after replacing the `client_id=` value with yours.
```txt
https://discord.com/oauth2/authorize?client_id=123456789&scope=bot
```

## Credits

Discord Application creation guide images taken from https://github.com/discord-tickets/docs

## License
Simple Applications Bot is licensed under the [GPLv3 license](https://github.com/discord-tickets/bot/blob/main/LICENSE).

This is not an official Discord product. It is not affiliated with nor endorsed by Discord Inc.
