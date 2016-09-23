# ==============================================================================
# >> IMPORTS
# ==============================================================================
# Python
import collections
import time
import pickle

# Source.Python
from commands.client import ClientCommandFilter
from commands.typed import TypedSayCommand
from commands import CommandReturn

from menus import PagedMenu
from menus import PagedOption

from players.entity import Player
from players.helpers import uniqueid_from_index
from players.helpers import index_from_uniqueid
from players.helpers import index_from_name

from messages import SayText2
from messages import TextMsg

from listeners import OnLevelEnd
from paths import CUSTOM_DATA_PATH
from events import Event
from filters.players import PlayerIter
from colors import RED
from engines.sound import Sound

from translations.strings import LangStrings



# ==============================================================================
# >> CONSTANTS
# ==============================================================================
# TODO Create a config file for (most of) these constants
# Ban durations
DURATIONS = {
    0: 'permanently',
    5 * 60: '5 minutes',
    15 * 60: '15 minutes',
    30 * 60: '30 minutes',
    60 * 60: '1 hour',
    3 * 60 * 60: '3 hours',
    6 * 60 * 60: '6 hours',
    12 * 60 * 60: '12 hours',
    24 * 60 * 60: '1 day',
    3 * 24 * 60 * 60: '3 days',
    7 * 24 * 60 * 60: '7 days',
}

# Path to the ban database
BAN_DATABASE = CUSTOM_DATA_PATH / 'ctban' / 'bans.db'

# Number of leavers to track
TRACKED_LEAVERS_NO = 5

# Number of freekillers to track
TRACKED_FREEKILLERS_NO = 5

# Prefix for messages
MESSAGE_PREFIX = '{}[CT Ban]\1'.format(RED)

# Sound file to play, relative to sound/
SOUND_FILE = Sound('buttons/button11.wav')

# Translation strings
TRANS = LangStrings('ctban')


# ==============================================================================
# >> CLASSES
# ==============================================================================
class BanSystem(dict):
    def __init__(self):
        """Initialize the ban system by loading the ban database (if existant)."""
        self.leavers = collections.deque(maxlen=TRACKED_LEAVERS_NO)
        self.freekillers = collections.deque(maxlen=TRACKED_FREEKILLERS_NO)
        try:
            with BAN_DATABASE.open('rb') as f:
                self.update(pickle.load(f))
        except FileNotFoundError:
            pass

    def save(self):
        """Write all bans to the database file."""
        try:
            BAN_DATABASE.parent.makedirs()
        except FileExistsError:
            pass

        with BAN_DATABASE.open('wb') as f:
            pickle.dump(self, f)

    def add_ban(self, uniqueid, duration, name):
        """Add a ban.
        
        :param str uniqueid:
            Unique ID of the player that should receive a ban.
        :param int duration:
            Duration of the ban in seconds. Use 0 for a permanent ban.
        :param str name:
            Name of the player to ban.
        """
        self[uniqueid] = (0 if duration == 0 else time.time() + duration, name)
        try:
            index = index_from_uniqueid(uniqueid)
        except ValueError:
            pass
        else:
            player = Player(index)
            player.team = 2

        try:
            self.leavers.remove((uniqueid, name))
        except ValueError:
            pass

        try:
            self.freekillers.remove((uniqueid, name))
        except ValueError:
            pass

    def is_banned(self, uniqueid):
        """Return True if the given unique ID is banned.
        
        :param str uniqueid:
            Unique ID of the player that should be checked.
        :rtype: bool
        """
        try:
            ban_time, name = self[uniqueid]
        except KeyError:
            return False

        return ban_time == 0 or time.time() < ban_time

    def remove_ban(self, uniqueid):
        """Remove the ban from the given unique ID.
        
        :param str uniqueid:
            Unique ID of the player that should be unbanned.
        :return:
            Ban duration and the name of the player or (None, None).
        :rtype: tuple
        """
        return self.pop(uniqueid, (None, None))

    def cleanup(self):
        """Remove all bans that expired and save the database."""
        now = time.time()
        for uniqueid, (ban_time, name) in tuple(self.items()):
            if ban_time != 0 and now >= ban_time:
                del self[uniqueid]

        self.save()

    def track_leaver(self, uniqueid, name):
        """Add a leaver to the tracking list for leavers.
        
        :param str uniqueid:
            Unique ID of the player to track.
        :param str name:
            Name of the player to track.
        """
        if self.is_banned(uniqueid):
            return

        data = (uniqueid, name)
        if data not in self.leavers:
            self.leavers.append(data)

    def track_freekiller(self, uniqueid, name):
        """Add a freekiller to the tracking list for freekillers.
        
        :param str uniqueid:
            Unique ID of the player to track.
        :param str name:
            Name of the player to track.
        """
        if self.is_banned(uniqueid):
            return

        data = (uniqueid, name)
        if data not in self.freekillers:
            self.freekillers.append(data)

ban_system = BanSystem()


# ==============================================================================
# >> BAN SYSTEM UPDATER
# ==============================================================================
@OnLevelEnd
def on_level_end():
    ban_system.cleanup()


# ==============================================================================
# >> ADMIN BAN MENU
# ==============================================================================
# TODO: Add permissions for each of these entries
admin_ban_menu = PagedMenu(
    [
        PagedOption(TRANS['menu:ban'], lambda: ct_menu),
        PagedOption(TRANS['menu:ban_leaver'], lambda: leaver_menu),
        PagedOption(TRANS['menu:ban_freekiller'], lambda: freekillers_menu),
        PagedOption(TRANS['menu:unban_player'], lambda: unban_menu)
    ],
    title=TRANS['menu:title']
)


@admin_ban_menu.register_select_callback
def on_admin_ban_menu_select(menu, index, option):
    return option.value()


# ==============================================================================
# >> PLAYER MENU
# ==============================================================================
ct_menu = PagedMenu(
    title=TRANS['menu:ban'],
    parent_menu=admin_ban_menu)

freekillers_menu = PagedMenu(
    title=TRANS['menu:ban_freekiller'],
    parent_menu=admin_ban_menu
)

leaver_menu = PagedMenu(
    title=TRANS['menu:ban_leaver'],
    parent_menu=admin_ban_menu
)

@ct_menu.register_build_callback
def on_active_player_menu_build(menu, index):
    menu.clear()
    for player in PlayerIter(['ct']):
        if player.index == index:
            continue

        menu.append(PagedOption(player.name, (player.uniqueid, player.name)))

@leaver_menu.register_build_callback
def on_leaver_menu_build(menu, index):
    menu.clear()
    for uniqueid, name in ban_system.leavers:
        menu.append(PagedOption(name, (uniqueid, name)))

@freekillers_menu.register_build_callback
def on_freekillers_menu_build(menu, index):
    menu.clear()
    for uniqueid, name in ban_system.freekillers:
        menu.append(PagedOption(name, (uniqueid, name)))

@leaver_menu.register_select_callback
@ct_menu.register_select_callback
@freekillers_menu.register_select_callback
def on_active_player_menu_select(menu, index, option):
    return create_ban_time_menu(menu, *option.value)


# ==============================================================================
# >> UNBAN MENU
# ==============================================================================
unban_menu = PagedMenu(
    title=TRANS['menu:unban_player'],
    parent_menu=admin_ban_menu)

@unban_menu.register_build_callback
def on_unban_menu_build(menu, index):
    menu.clear()
    bans = tuple(ban_system.items())
    sorted_bans = sorted(bans, key=lambda key: key[1][1])
    for uniqueid, (ban_time, name) in sorted_bans:
        menu.append(PagedOption('{} ({})'.format(name, uniqueid), uniqueid))

@unban_menu.register_select_callback
def on_unban_menu_select(menu, index, option):
    ban_time, name = ban_system.remove_ban(option.value)
    if ban_time is not None:
        SayText2(TRANS['player:remove_ban']).send(
            index, prefix=MESSAGE_PREFIX, name=name)


# ==============================================================================
# >> BAN TIME MENU
# ==============================================================================
def create_ban_time_menu(parent_menu, uniqueid, name):
    ban_time_menu = PagedMenu(
        title=TRANS['menu:ban_time'], parent_menu=parent_menu)
        
    for duration, display_name in sorted(DURATIONS.items()):
        ban_time_menu.append(
            PagedOption(display_name, (uniqueid, name, duration)))

    ban_time_menu.select_callback = on_ban_time_menu_select
    return ban_time_menu

def on_ban_time_menu_select(menu, index, option):
    uniqueid, name, duration = option.value
    ban_system.add_ban(uniqueid, duration, name)
    SayText2(TRANS['player:add_ban']).send(prefix=MESSAGE_PREFIX, name=name)

    
# ==============================================================================
# >> EVENTS
# ==============================================================================
@Event('player_disconnect')
def on_player_disconnect(event):
    player = Player.from_userid(event['userid'])
    ban_system.track_leaver(player.uniqueid, player.name)


@Event('player_death')
def on_player_death(event):
    attacker_id = event['attacker']
    if event['userid'] == attacker_id:
        return

    try:
        attacker = Player.from_userid(attacker_id)
    except ValueError:
        return

    ban_system.track_freekiller(attacker.uniqueid, attacker.name)


@ClientCommandFilter
def on_client_command(command, index):
    if command[0].lower() != 'jointeam':
        return

    if not (len(command) == 1 or command[1] not in ('1', '2')):
        return

    uniqueid = uniqueid_from_index(index)
    if not ban_system.is_banned(uniqueid):
        return

    # TODO: Re-display team selection menu
    SOUND_FILE.play()
    TextMsg(TRANS['player:banned']).send(index)
    return CommandReturn.BLOCK


# ==============================================================================
# >> SAY COMMANDS
# ==============================================================================
@TypedSayCommand('!ctban', 'ctban.open')
def on_ctban_open(info):
    admin_ban_menu.send(info.index)
    return CommandReturn.BLOCK


# TODO: Display more info
@TypedSayCommand('!is_banned', 'ctban.is_banned')
def command_is_banned(info, target):
    player = None
    if target.startswith('#'):
        try:
            player = Player.from_userid(int(target[1:]))
        except:
            pass
    else:
        try:
            player = Player(index_from_name(target))
        except ValueError:
            pass
            
    if player is None:
        SayText2(TRANS['player:not_found']).send(
            info.index, prefix=MESSAGE_PREFIX, name=target)
        return CommandReturn.BLOCK
    
    if ban_system.is_banned(player.uniqueid):
        msg = 'player:is_banned'
    else:
        msg = 'player:not_banned'

    SayText2(TRANS[msg]).send(
        info.index, prefix=MESSAGE_PREFIX, name=player.name)
    return CommandReturn.BLOCK
