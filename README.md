# CT-Ban
A Source.Python plugin that is able to ban players from the CT team.

## Installation
1. Download the plugin and extract it to your game folder.
2. Load the plugin with ``sp plugin load ctban``.
3. Configure permissions: http://wiki.sourcepython.com/general/config-auth.html
  1. ``ctban.open`` to open the CT Ban menu. 
  2. ``ctban.is_banned`` for the ``!is_banned`` say command.

## Usage
Type ``!ctban`` in the chat to open the CT Ban menu.

A menu should appear that allows you to:

1. Ban CT
2. Ban freekiller
3. Ban leaver
4. Unban player

Type ```!is_banned <playername | id>``` in the chat to check if a player is banned or not.

Example: ```!is_banned Ayuto``` or with a user ID ```!is_banned #2```
