"""
Unifier - A sophisticated Discord bot uniting servers and platforms
Copyright (C) 2023-present  UnifierHQ

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import nextcord
from nextcord.ext import commands
from utils import ui, log
import json
import os
import sys
import re
import tomli
import tomli_w
import shutil
import importlib

class Emojis:
    def __init__(self, data=None, devmode=False):
        if devmode:
            with open('emojis/devbase.json', 'r') as file:
                base = json.load(file)
        else:
            with open('emojis/base.json', 'r') as file:
                base = json.load(file)

        if data:
            for key in base['emojis'].keys():
                if not key in data['emojis'].keys():
                    data['emojis'].update({key: data['emojis'][key]})
        else:
            data = base

        self.back = data['emojis']['back'][0]
        self.prev = data['emojis']['prev'][0]
        self.next = data['emojis']['next'][0]
        self.first = data['emojis']['first'][0]
        self.last = data['emojis']['last'][0]
        self.search = data['emojis']['search'][0]
        self.command = data['emojis']['command'][0]
        self.install = data['emojis']['install'][0]
        self.success = data['emojis']['success'][0]
        self.warning = data['emojis']['warning'][0]
        self.error = data['emojis']['error'][0]
        self.rooms = data['emojis']['rooms'][0]
        self.emoji = data['emojis']['emoji'][0]
        self.leaderboard = data['emojis']['leaderboard'][0]

def status(code):
    if code != 0:
        raise RuntimeError("install failed")

class EmergencyUpgrader(commands.Cog):
    def __init__(self,bot):
        global language
        self.bot = bot
        self.logger = log.buildlogger(self.bot.package, 'eupgrader', self.bot.loglevel)

    async def copy(self, src, dst):
        await self.bot.loop.run_in_executor(None, lambda: shutil.copy2(src, dst))

    async def preunload(self, extension):
        """Performs necessary steps before unloading."""
        info = None
        plugin_name = None
        if extension.startswith('cogs.'):
            extension = extension.replace('cogs.', '', 1)
        for plugin in os.listdir('plugins'):
            if extension + '.json' == plugin:
                plugin_name = plugin[:-5]
                try:
                    with open('plugins/' + plugin) as file:
                        info = json.load(file)
                except:
                    continue
                break
            else:
                try:
                    with open('plugins/' + plugin) as file:
                        info = json.load(file)
                except:
                    continue
                if extension + '.py' in info['modules']:
                    plugin_name = plugin[:-5]
                    break
        if not plugin_name:
            return
        if plugin_name == 'system':
            return
        if not info:
            raise ValueError('Invalid plugin')
        if not info['shutdown']:
            return
        script = importlib.import_module('utils.' + plugin_name + '_check')
        await script.check(self.bot)

    @commands.command(hidden=True,description='Upgrades Unifier or a plugin.')
    async def emergency_upgrade(self, ctx, plugin='system', *, args=''):
        if not ctx.author.id == self.bot.config['owner']:
            return

        with open('plugins/system.json', 'r') as file:
            current = json.load(file)

        if current['release'] >= 75:
            return await ctx.send('You\'re on a patched version. Emergency Upgrader is not needed.')

        if os.name == "win32":
            embed = nextcord.Embed(
                title=f'{self.bot.ui_emojis.error} Can\'t upgrade Unifier',
                description=('Unifier cannot upgrade itself on Windows. Please use an OS with the bash console (Linux/'+
                             'macOS/etc).'),
                color=self.bot.colors.error
            )
            return await ctx.send(embed=embed)

        args = args.split(' ')
        force = False
        ignore_backup = False
        no_backup = False
        if 'force' in args:
            force = True
        if 'ignore-backup' in args:
            ignore_backup = True
        if 'no-backup' in args:
            no_backup = True

        plugin = plugin.lower()

        if plugin=='system':
            embed = nextcord.Embed(
                title=f'{self.bot.ui_emojis.install} Checking for upgrades...',
                description='Getting latest version from remote'
            )
            msg = await ctx.send(embed=embed)
            available = []
            try:
                os.system('rm -rf ' + os.getcwd() + '/update_check')
                await self.bot.loop.run_in_executor(None, lambda: os.system(
                    'git clone --branch ' + self.bot.config['branch'] + ' ' + self.bot.config[
                        'check_endpoint'] + ' ' + os.getcwd() + '/update_check'))
                with open('plugins/system.json', 'r') as file:
                    current = json.load(file)
                with open('update_check/update.json', 'r') as file:
                    new = json.load(file)
                if new['release'] > current['release'] or force:
                    available.append([new['version'], 'Release version', new['release'], -1, new['reboot']])
                index = 0
                for legacy in new['legacy']:
                    if (
                            legacy['lower'] <= current['release'] <= legacy['upper'] and (
                                legacy['release'] > (
                                    current['legacy'] if 'legacy' in current.keys() else -1
                                ) or force
                            )
                    ):
                        available.append([legacy['version'], 'Legacy version', legacy['release'], index, legacy['reboot']])
                    index += 1
                update_available = len(available) >= 1
            except:
                embed.title = f'{self.bot.ui_emojis.error} Failed to check for updates'
                embed.description = 'Could not find a valid update.json file on remote'
                embed.colour = self.bot.colors.error
                return await msg.edit(embed=embed)
            if not update_available:
                embed.title = f'{self.bot.ui_emojis.success} No updates available'
                embed.description = 'Unifier is up-to-date.'
                embed.colour = self.bot.colors.success
                return await msg.edit(embed=embed)
            selected = 0
            interaction = None
            while True:
                release = available[selected][2]
                version = available[selected][0]
                legacy = available[selected][3] > -1
                reboot = available[selected][4]
                embed.title = f'{self.bot.ui_emojis.install} Update available'
                embed.description = f'An update is available for Unifier!\n\nCurrent version: {current["version"]} (`{current["release"]}`)\nNew version: {version} (`{release}`)'
                embed.remove_footer()
                embed.colour = 0xffcc00
                if legacy:
                    should_reboot = reboot >= (current['legacy'] if 'legacy' in current.keys() and
                                               type(current['legacy']) is int else -1)
                else:
                    should_reboot = reboot >= current['release']
                if should_reboot:
                    embed.set_footer(text='The bot will need to reboot to apply the new update.')
                selection = nextcord.ui.StringSelect(
                    placeholder='Select version...',
                    max_values=1,
                    min_values=1,
                    custom_id='selection',
                    disabled=len(available)==1
                )
                index = 0
                for update_option in available:
                    selection.add_option(
                        label=update_option[0],
                        description=update_option[1],
                        value=f'{index}',
                        default=index==selected
                    )
                    index += 1
                btns = ui.ActionRow(
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.green, label='Upgrade', custom_id=f'accept',
                        disabled=False
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.gray, label='Nevermind', custom_id=f'reject',
                        disabled=False
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.link, label='More info',
                        url=f'https://github.com/UnifierHQ/unifier/releases/tag/{version}'
                    )
                )
                components = ui.MessageComponents()
                components.add_rows(ui.ActionRow(selection),btns)
                if not interaction:
                    await msg.edit(embed=embed, view=components)
                else:
                    await interaction.response.edit_message(embed=embed, view=components)

                def check(interaction):
                    return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

                try:
                    interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
                except:
                    return await msg.edit(view=None)
                if interaction.data['custom_id'] == 'reject':
                    return await interaction.response.edit_message(view=None)
                elif interaction.data['custom_id'] == 'accept':
                    break
                elif interaction.data['custom_id'] == 'selection':
                    selected = int(interaction.data['values'][0])
            self.logger.info('Upgrade confirmed, preparing...')
            if not no_backup:
                embed.title = f'{self.bot.ui_emojis.install} Backing up...'
                embed.description = 'Your data is being backed up.'
                await interaction.response.edit_message(embed=embed, view=None)
            try:
                if no_backup:
                    raise ValueError()
                folder = os.getcwd() + '/old'
                try:
                    os.mkdir(folder)
                except:
                    pass
                folder = os.getcwd() + '/old/cogs'
                try:
                    os.mkdir(folder)
                except:
                    pass
                for file in os.listdir(os.getcwd() + '/cogs'):
                    self.logger.debug('Backing up: ' + os.getcwd() + '/cogs/' + file)
                    os.system('cp ' + os.getcwd() + '/cogs/' + file + ' ' + os.getcwd() + '/old/cogs/' + file)
                self.logger.debug('Backing up: ' + os.getcwd() + '/unifier.py')
                os.system('cp ' + os.getcwd() + '/unifier.py ' + os.getcwd() + '/old/unifier.py')
                self.logger.debug('Backing up: ' + os.getcwd() + '/data.json')
                os.system('cp ' + os.getcwd() + '/data.json ' + os.getcwd() + '/old/data.json')
                self.logger.debug('Backing up: ' + os.getcwd() + '/config.json')
                os.system('cp ' + os.getcwd() + '/config.json ' + os.getcwd() + '/old/config.json')
                self.logger.debug('Backing up: ' + os.getcwd() + '/update.json')
                os.system('cp ' + os.getcwd() + '/update.json ' + os.getcwd() + '/old/update.json')
            except:
                if no_backup:
                    self.logger.warning('Backup skipped, requesting final confirmation.')
                    embed.description = '- :x: Your files have **NOT BEEN BACKED UP**! Data loss or system failures may occur if the upgrade fails!\n- :wrench: Any modifications you made to Unifier will be wiped, unless they are a part of the new upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
                elif ignore_backup:
                    self.logger.warning('Backup failed, continuing anyways')
                    embed.description = '- :x: Your files **COULD NOT BE BACKED UP**! Data loss or system failures may occur if the upgrade fails!\n- :wrench: Any modifications you made to Unifier will be wiped, unless they are a part of the new upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
                else:
                    self.logger.error('Backup failed, abort upgrade.')
                    embed.title = f'{self.bot.ui_emojis.error} Backup failed'
                    embed.description = 'Unifier could not create a backup. The upgrade has been aborted.'
                    embed.colour = self.bot.colors.error
                    await msg.edit(embed=embed)
                    raise
            else:
                self.logger.info('Backup complete, requesting final confirmation.')
                embed.description = '- :inbox_tray: Your files have been backed up to `[Unifier root directory]/old.`\n- :wrench: Any modifications you made to Unifier will be wiped, unless they are a part of the new upgrade.\n- :warning: Once started, you cannot abort the upgrade.'
            embed.title = f'{self.bot.ui_emojis.install} Start the upgrade?'
            components = ui.MessageComponents()
            components.add_row(btns)
            if no_backup:
                await interaction.response.edit_message(embed=embed, view=components)
            else:
                await msg.edit(embed=embed, view=components)
            try:
                interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
            except:
                btns.items[0].disabled = True
                btns.items[1].disabled = True
                components = ui.MessageComponents()
                components.add_row(btns)
                return await msg.edit(view=components)
            if interaction.data['custom_id'] == 'reject':
                btns.items[0].disabled = True
                btns.items[1].disabled = True
                components = ui.MessageComponents()
                components.add_row(btns)
                return await interaction.response.edit_message(view=components)
            self.logger.debug('Upgrade confirmed, beginning upgrade')
            embed.title = f'{self.bot.ui_emojis.install} Upgrading Unifier'
            embed.description = ':hourglass_flowing_sand: Downloading updates\n:x: Installing updates\n:x: Reloading modules'
            await interaction.response.edit_message(embed=embed, view=None)
            self.logger.info('Starting upgrade')
            try:
                self.logger.debug('Purging old update files')
                os.system('rm -rf ' + os.getcwd() + '/update')
                self.logger.info('Downloading from remote repository...')
                await self.bot.loop.run_in_executor(None, lambda: os.system(
                    'git clone --branch ' + version + ' --single-branch --depth 1 ' + self.bot.config[
                        'files_endpoint'] + '/unifier.git ' + os.getcwd() + '/update'
                ))
                self.logger.debug('Confirming download...')
                x = open(os.getcwd() + '/update/plugins/system.json', 'r')
                x.close()
                self.logger.debug('Download confirmed, proceeding with upgrade')
            except:
                self.logger.exception('Download failed, no rollback required')
                embed.title = f'{self.bot.ui_emojis.error} Upgrade failed'
                embed.description = 'Could not download updates. No rollback is required.'
                embed.colour = self.bot.colors.error
                await msg.edit(embed=embed)
                return
            try:
                self.logger.debug('Installing dependencies')
                x = open('update/requirements.txt')
                newdeps = x.read().split('\n')
                x.close()
                try:
                    x = open('requirements.txt')
                    olddeps = x.read().split('\n')
                    x.close()
                except:
                    self.logger.warning('Could not find requirements.txt, installing all dependencies')
                    olddeps = []
                for dep in olddeps:
                    try:
                        newdeps.remove(dep)
                    except:
                        pass
                if len(newdeps) > 0:
                    self.logger.debug('Installing: ' + ' '.join(newdeps))
                    await self.bot.loop.run_in_executor(None, lambda: status(os.system(
                        'python3 -m pip install ' + '"' + '" "'.join(newdeps) + '"')
                    ))
            except:
                self.logger.exception('Dependency installation failed, no rollback required')
                embed.title = f'{self.bot.ui_emojis.error} Upgrade failed'
                embed.description = 'Could not install dependencies. No rollback is required.'
                embed.colour = self.bot.colors.error
                await msg.edit(embed=embed)
                return
            try:
                self.logger.info('Installing upgrades')
                embed.description = ':white_check_mark: Downloading updates\n:hourglass_flowing_sand: Installing updates\n:x: Reloading modules'
                await msg.edit(embed=embed)
                self.logger.debug('Installing: ' + os.getcwd() + '/update/unifier.py')
                status(os.system('cp ' + os.getcwd() + '/update/unifier.py ' + os.getcwd() + '/unifier.py'))
                self.logger.debug('Installing: ' + os.getcwd() + '/update/requirements.txt')
                status(os.system('cp ' + os.getcwd() + '/update/requirements.txt ' + os.getcwd() + '/requirements.txt'))
                self.logger.debug('Installing: ' + os.getcwd() + '/update_check/update.json')
                if legacy:
                    current['version'] = version
                    current['legacy'] = release
                    with open('plugins/system.json', 'w+') as file:
                        json.dump(current,file)
                else:
                    status(os.system('cp ' + os.getcwd() + '/update_check/update.json ' + os.getcwd() + '/plugins/system.json'))
                    with open('plugins/system.json', 'r') as file:
                        newcurrent = json.load(file)
                    newcurrent.pop('legacy')
                    with open('plugins/system.json', 'w+') as file:
                        json.dump(newcurrent, file)
                for file in os.listdir(os.getcwd() + '/update/cogs'):
                    self.logger.debug('Installing: ' + os.getcwd() + '/update/cogs/' + file)
                    status(
                        os.system('cp ' + os.getcwd() + '/update/cogs/' + file + ' ' + os.getcwd() + '/cogs/' + file))
                for file in os.listdir(os.getcwd() + '/update/utils'):
                    self.logger.debug('Installing: ' + os.getcwd() + '/update/utils/' + file)
                    status(
                        os.system('cp ' + os.getcwd() + '/update/utils/' + file + ' ' + os.getcwd() + '/utils/' + file))
                self.logger.debug('Updating config.json')
                with open('config.json', 'r') as file:
                    oldcfg = json.load(file)
                with open('update/config.json', 'r') as file:
                    newcfg = json.load(file)
                for key in newcfg:
                    if not key in list(oldcfg.keys()):
                        oldcfg.update({key: newcfg[key]})
                with open('config.json', 'w') as file:
                    json.dump(oldcfg, file, indent=4)
                if should_reboot:
                    self.bot.update = True
                    self.logger.info('Upgrade complete, reboot required')
                    embed.title = f'{self.bot.ui_emojis.success} Restart to apply upgrade'
                    embed.description = f'The upgrade was successful. Please reboot the bot.'
                    embed.colour = self.bot.colors.success
                    await msg.edit(embed=embed)
                else:
                    self.logger.info('Restarting extensions')
                    embed.description = ':white_check_mark: Downloading updates\n:white_check_mark: Installing updates\n:hourglass_flowing_sand: Reloading modules'
                    await msg.edit(embed=embed)
                    for cog in list(self.bot.extensions):
                        self.logger.debug('Restarting extension: ' + cog)
                        await self.preunload(cog)
                        self.bot.reload_extension(cog)
                    self.logger.info('Upgrade complete')
                    embed.title = f'{self.bot.ui_emojis.success} Upgrade successful'
                    embed.description = 'The upgrade was successful! :partying_face:'
                    embed.colour = self.bot.colors.success
                    await msg.edit(embed=embed)
            except:
                self.logger.exception('Upgrade failed, attempting rollback')
                embed.title = f'{self.bot.ui_emojis.error} Upgrade failed'
                embed.colour = self.bot.colors.error
                try:
                    self.logger.debug('Reverting: ' + os.getcwd() + '/unifier.py')
                    status(os.system('cp ' + os.getcwd() + '/old/unifier.py ' + os.getcwd() + '/unifier.py'))
                    self.logger.debug('Reverting: ' + os.getcwd() + '/data.json')
                    status(os.system('cp ' + os.getcwd() + '/old/data.json ' + os.getcwd() + '/data.json'))
                    self.logger.debug('Reverting: ' + os.getcwd() + '/plugins/system.json')
                    status(os.system('cp ' + os.getcwd() + '/old/plugins/system.json ' + os.getcwd() + '/plugins/system.json'))
                    self.logger.debug('Reverting: ' + os.getcwd() + '/config.json')
                    status(os.system('cp ' + os.getcwd() + '/old/config.json ' + os.getcwd() + '/config.json'))
                    for file in os.listdir(os.getcwd() + '/old/cogs'):
                        self.logger.debug('Reverting: ' + os.getcwd() + '/cogs/' + file)
                        status(
                            os.system('cp ' + os.getcwd() + '/old/cogs/' + file + ' ' + os.getcwd() + '/cogs/' + file))
                    self.logger.info('Rollback success')
                    embed.description = 'The upgrade failed, and all files have been rolled back.'
                except:
                    self.logger.exception('Rollback failed')
                    self.logger.critical(
                        'The rollback failed. Visit https://unichat-wiki.pixels.onl/setup-selfhosted/upgrading-unifier/manual-rollback for recovery steps.')
                    embed.description = 'The upgrade failed, and the bot may now be in a crippled state.\nPlease check console logs for more info.'
                await msg.edit(embed=embed)
                return
        else:
            embed = nextcord.Embed(title=f'{self.bot.ui_emojis.install} Downloading extension...', description='Getting extension files from remote')

            try:
                with open('plugins/'+plugin+'.json') as file:
                    plugin_info = json.load(file)
            except:
                embed.title = f'{self.bot.ui_emojis.error} Plugin not found'
                embed.description = 'The plugin could not be found.'
                if plugin=='force':
                    embed.description = embed.description + f'\n\n**Hint**: If you\'re trying to force upgrade, run `{self.bot.command_prefix}upgrade system force`'
                embed.colour = self.bot.colors.error
                await ctx.send(embed=embed)
                return
            embed.set_footer(text='Only install plugins from trusted sources!')
            msg = await ctx.send(embed=embed)
            url = plugin_info['repository']
            try:
                os.system('rm -rf ' + os.getcwd() + '/plugin_install')
                await self.bot.loop.run_in_executor(None, lambda: status(os.system(
                    'git clone ' + url + ' ' + os.getcwd() + '/plugin_install')))
                with open('plugin_install/plugin.json', 'r') as file:
                    new = json.load(file)
                if not bool(re.match("^[a-z0-9_-]*$", new['id'])):
                    embed.title = f'{self.bot.ui_emojis.error} Invalid plugin.json file'
                    embed.description = 'Plugin IDs must be alphanumeric and may only contain lowercase letters, numbers, dashes, and underscores.'
                    embed.colour = self.bot.colors.error
                    await msg.edit(embed=embed)
                    return
                if new['release'] <= plugin_info['release'] and not force:
                    embed.title = f'{self.bot.ui_emojis.success} Plugin up to date'
                    embed.description = f'This plugin is already up to date!'
                    embed.colour = self.bot.colors.success
                    await msg.edit(embed=embed)
                    return
                plugin_id = new['id']
                name = new['name']
                desc = new['description']
                version = new['version']
                modules = new['modules']
                utilities = new['utils']
                services = new['services'] if 'services' in new.keys() else []
            except:
                embed.title = f'{self.bot.ui_emojis.error} Failed to update plugin'
                embed.description = 'The repository URL or the plugin.json file is invalid.'
                embed.colour = self.bot.colors.error
                await msg.edit(embed=embed)
                raise
            embed.title = f'{self.bot.ui_emojis.install} Update `{plugin_id}`?'
            embed.description = f'Name: `{name}`\nVersion: `{version}`\n\n{desc}'
            embed.colour = 0xffcc00
            btns = ui.ActionRow(
                nextcord.ui.Button(style=nextcord.ButtonStyle.green, label='Update', custom_id=f'accept', disabled=False),
                nextcord.ui.Button(style=nextcord.ButtonStyle.gray, label='Nevermind', custom_id=f'reject', disabled=False)
            )
            components = ui.MessageComponents()
            components.add_row(btns)
            await msg.edit(embed=embed, view=components)

            def check(interaction):
                return interaction.user.id == ctx.author.id and interaction.message.id == msg.id

            try:
                interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
            except:
                btns.items[0].disabled = True
                btns.items[1].disabled = True
                components = ui.MessageComponents()
                components.add_row(btns)
                return await msg.edit(view=components)
            if interaction.data['custom_id'] == 'reject':
                btns.items[0].disabled = True
                btns.items[1].disabled = True
                components = ui.MessageComponents()
                components.add_row(btns)
                return await interaction.response.edit_message(view=components)

            await interaction.response.edit_message(embed=embed, view=None)
            try:
                try:
                    if 'requirements' in list(new.keys()):
                        self.logger.debug('Installing dependencies')
                        newdeps = new['requirements']
                        try:
                            olddeps = plugin_info['requirements']
                        except:
                            olddeps = []
                        for dep in olddeps:
                            if dep in newdeps:
                                newdeps.remove(dep)
                        if len(newdeps) > 0:
                            self.logger.debug('Installing: ' + ' '.join(newdeps))
                            await self.bot.loop.run_in_executor(None, lambda: status(
                                os.system('python3 -m pip install --no-dependencies ' + '"' + '" "'.join(newdeps) + '"')
                            ))
                except:
                    self.logger.exception('Dependency installation failed')
                    raise RuntimeError()
                self.logger.info('Upgrading Plugin')
                for module in modules:
                    self.logger.debug('Installing: ' + os.getcwd() + '/plugin_install/' + module)
                    status(os.system(
                        'cp ' + os.getcwd() + '/plugin_install/' + module + ' ' + os.getcwd() + '/cogs/' + module))
                for util in utilities:
                    self.logger.debug('Installing: ' + os.getcwd() + '/plugin_install/' + util)
                    status(os.system(
                        'cp ' + os.getcwd() + '/plugin_install/' + util + ' ' + os.getcwd() + '/utils/' + util))
                if 'emojis' in services:
                    self.logger.info('Uninstalling previous Emoji Pack')
                    home_guild = self.bot.get_guild(self.bot.config['home_guild'])
                    with open(f'emojis/{plugin_id}.json', 'r') as file:
                        oldemojipack = json.load(file)
                    with open('plugin_install/emoji.json', 'r') as file:
                        emojipack = json.load(file)
                    toreplace = []
                    for emojiname in oldemojipack['emojis']:
                        oldversion = oldemojipack['emojis'][emojiname][1]
                        ignore_replace = False
                        try:
                            newversion = emojipack['emojis'][emojiname][1]
                        except:
                            ignore_replace = True
                            newversion = oldversion + 1
                        if oldversion < newversion:
                            emoji = oldemojipack['emojis'][emojiname][0]
                            if (emoji.startswith('<:') or emoji.startswith('<a:')) and emoji.endswith('>'):
                                emoji_id = int(emoji.split(':')[2].replace('>',''))
                                self.logger.debug(f'Removing: {emoji_id}')
                                for emoji_obj in home_guild.emojis:
                                    if emoji_obj.id==emoji_id:
                                        await emoji_obj.delete()
                            if not ignore_replace:
                                toreplace.append(emojiname)

                    self.logger.info('Installing new Emoji Pack')
                    home_guild = self.bot.get_guild(self.bot.config['home_guild'])
                    for emojiname in emojipack['emojis']:
                        if emojiname in toreplace or not emojiname in oldemojipack['emojis'].keys():
                            self.logger.debug(
                                'Installing: ' + os.getcwd() + '/plugin_install/emojis/' + emojipack['emojis'][emojiname][0])
                            file = 'plugin_install/emojis/' + emojipack['emojis'][emojiname][0]
                            emoji = await home_guild.create_custom_emoji(name=emojiname, image=nextcord.File(fp=file))
                            emojipack['emojis'][
                                emojiname][0] = f'<a:{emoji.name}:{emoji.id}>' if emoji.animated else f'<:{emoji.name}:{emoji.id}>'
                        else:
                            emojipack['emojis'][emojiname][0] = oldemojipack['emojis'][emojiname][0]
                    emojipack['installed'] = True
                    with open(f'emojis/{plugin_id}.json', 'w+') as file:
                        json.dump(emojipack, file, indent=2)
                    with open(f'emojis/current.json', 'r') as file:
                        currentdata = json.load(file)
                    if currentdata['id']==plugin_id:
                        emojipack.update({'id': plugin_id})
                        with open(f'emojis/current.json', 'w+') as file:
                            json.dump(emojipack, file, indent=2)
                        self.bot.ui_emojis = Emojis(data=emojipack)
                self.logger.info('Registering plugin')
                status(
                    os.system(
                        'cp ' + os.getcwd() + '/plugin_install/plugin.json' + ' ' + os.getcwd() + '/plugins/' + plugin_id + '.json'))
                with open('plugins/' + plugin_id + '.json') as file:
                    plugin_info = json.load(file)
                    plugin_info.update({'repository': url})
                with open('plugins/' + plugin_id + '.json', 'w') as file:
                    json.dump(plugin_info, file)
                self.logger.info('Reloading extensions')
                for module in modules:
                    modname = 'cogs.' + module[:-3]
                    if modname in list(self.bot.extensions):
                        self.logger.debug('Reloading extension: ' + modname)
                        await self.preunload(modname)
                        self.bot.reload_extension(modname)
                self.logger.debug('Upgrade complete')
                embed.title = f'{self.bot.ui_emojis.success} Upgrade successful'
                embed.description = 'The upgrade was successful! :partying_face:'
                embed.colour = self.bot.colors.success
                await msg.edit(embed=embed)
            except:
                self.logger.exception('Upgrade failed')
                embed.title = f'{self.bot.ui_emojis.error} Upgrade failed'
                embed.description = 'The upgrade failed.'
                embed.colour = self.bot.colors.error
                await msg.edit(embed=embed)
                return

def setup(bot):
    bot.add_cog(EmergencyUpgrader(bot))
