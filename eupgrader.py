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
from utils import ui, langmgr, restrictions as r, log
import json
import os
import sys
import re
import tomli
import tomli_w
import shutil
import importlib

restrictions = r.Restrictions()
language = langmgr.partial()
language.load()

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

        restrictions.attach_bot(self.bot)
        language = self.bot.langmgr

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
    @restrictions.owner()
    async def emergency_upgrade(self, ctx, plugin='system', *, args=''):
        if not ctx.author.id == self.bot.config['owner']:
            return

        selector = language.get_selector(ctx)

        if self.bot.update:
            return await ctx.send(selector.rawget('disabled','sysmgr.reload'))

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
                title=f'{self.bot.ui_emojis.install} {selector.get("checking_title")}',
                description=selector.get('checking_body')
            )
            msg = await ctx.send(embed=embed)
            available = []
            try:
                await self.bot.loop.run_in_executor(None, lambda: shutil.rmtree('update_check'))
                await self.bot.loop.run_in_executor(None, lambda: os.system(
                    'git clone --branch ' + self.bot.config['branch'] + ' ' + self.bot.config[
                        'check_endpoint'] + ' update_check'))
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
                embed.title = f'{self.bot.ui_emojis.error} {selector.get("checkfail_title")}'
                embed.description = selector.get("checkfail_body")
                embed.colour = self.bot.colors.error
                return await msg.edit(embed=embed)
            if not update_available:
                embed.title = f'{self.bot.ui_emojis.success} {selector.get("noupdates_title")}'
                embed.description = selector.get("noupdates_body")
                embed.colour = self.bot.colors.success
                return await msg.edit(embed=embed)
            selected = 0
            interaction = None
            while True:
                release = available[selected][2]
                version = available[selected][0]
                legacy = available[selected][3] > -1
                reboot = available[selected][4]
                embed.title = f'{self.bot.ui_emojis.install} {selector.get("available_title")}'
                embed.description = selector.fget('available_body',values={
                    'current_ver':current['version'],'current_rel':current['release'],'new_ver':version,'new_rel':release
                })
                embed.remove_footer()
                embed.colour = 0xffcc00
                if legacy:
                    should_reboot = reboot >= (current['legacy'] if 'legacy' in current.keys() and
                                               type(current['legacy']) is int else -1)
                else:
                    should_reboot = reboot >= current['release']
                if should_reboot:
                    embed.set_footer(text=selector.get("reboot_required"))
                selection = nextcord.ui.StringSelect(
                    placeholder=selector.get("version"),
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
                        style=nextcord.ButtonStyle.green, label=selector.get("upgrade"), custom_id=f'accept',
                        disabled=False
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.gray, label=selector.rawget('nevermind','sysmgr.install'), custom_id=f'reject',
                        disabled=False
                    ),
                    nextcord.ui.Button(
                        style=nextcord.ButtonStyle.link, label=selector.get("moreinfo"),
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
                embed.title = f'{self.bot.ui_emojis.install} {selector.get("backup_title")}'
                embed.description = selector.get("backup_body")
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
                folder = os.getcwd() + '/old/utils'
                try:
                    os.mkdir(folder)
                except:
                    pass
                folder = os.getcwd() + '/old/languages'
                try:
                    os.mkdir(folder)
                except:
                    pass
                folder = os.getcwd() + '/old/plugins'
                try:
                    os.mkdir(folder)
                except:
                    pass
                folder = os.getcwd() + '/old/boot'
                try:
                    os.mkdir(folder)
                except:
                    pass
                for file in os.listdir(os.getcwd() + '/cogs'):
                    self.logger.debug('Backing up: ' + os.getcwd() + '/cogs/' + file)
                    try:
                        await self.copy('cogs/' + file, 'old/cogs/' + file)
                    except IsADirectoryError:
                        continue
                for file in os.listdir(os.getcwd() + '/utils'):
                    self.logger.debug('Backing up: ' + os.getcwd() + '/utils/' + file)
                    try:
                        await self.copy('utils/' + file, 'old/utils/' + file)
                    except IsADirectoryError:
                        continue
                for file in os.listdir(os.getcwd() + '/plugins'):
                    self.logger.debug('Backing up: ' + os.getcwd() + '/plugins/' + file)
                    try:
                        await self.copy('plugins/' + file, 'old/plugins/' + file)
                    except IsADirectoryError:
                        continue
                for file in os.listdir(os.getcwd() + '/languages'):
                    self.logger.debug('Backing up: ' + os.getcwd() + '/languages/' + file)
                    try:
                        await self.copy('languages/' + file, 'old/languages/' + file)
                    except IsADirectoryError:
                        continue
                for file in os.listdir(os.getcwd() + '/boot'):
                    self.logger.debug('Backing up: ' + os.getcwd() + '/boot/' + file)
                    try:
                        await self.copy('boot/' + file, 'old/boot/' + file)
                    except IsADirectoryError:
                        continue
                self.logger.debug('Backing up: ' + os.getcwd() + '/unifier.py')
                await self.copy('unifier.py', 'old/unifier.py')
                self.logger.debug('Backing up: ' + os.getcwd() + '/data.json')
                await self.copy('data.json', 'old/data.json')
                self.logger.debug('Backing up: ' + os.getcwd() + '/config.toml')
                await self.copy('config.toml', 'old/config.toml')
                self.logger.debug('Backing up: ' + os.getcwd() + '/boot_config.json')
                await self.copy('boot_config.json', 'old/boot_config.json')
            except:
                if no_backup:
                    self.logger.warning('Backup skipped, requesting final confirmation.')
                    embed.description = f'- :x: {selector.get("skipped_backup")}\n- :wrench: {selector.get("modification_wipe")}\n- :warning: {selector.get("no_abort")}'
                elif ignore_backup:
                    self.logger.warning('Backup failed, continuing anyways')
                    embed.description = f'- :x: {selector.get("failed_backup")}\n- :wrench: {selector.get("modification_wipe")}\n- :warning: {selector.get("no_abort")}'
                else:
                    self.logger.error('Backup failed, abort upgrade.')
                    embed.title = f'{self.bot.ui_emojis.error} {selector.get("backupfail_title")}'
                    embed.description = selector.get("backupfail_body")
                    embed.colour = self.bot.colors.error
                    await msg.edit(embed=embed)
                    raise
            else:
                self.logger.info('Backup complete, requesting final confirmation.')
                embed.description = f'- :inbox_tray: {selector.get("normal_backup")}\n- :wrench: {selector.get("modification_wipe")}\n- :warning: {selector.get("no_abort")}'
            embed.title = f'{self.bot.ui_emojis.install} {selector.get("start")}'
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
            embed.title = f'{self.bot.ui_emojis.install} {selector.get("upgrading")}'
            embed.description = f':hourglass_flowing_sand: {selector.get("downloading")}\n:x: {selector.get("installing")}\n:x: {selector.get("reloading")}'
            await interaction.response.edit_message(embed=embed, view=None)
            self.logger.info('Starting upgrade')
            try:
                self.logger.debug('Purging old update files')
                await self.bot.loop.run_in_executor(None, lambda: shutil.rmtree('update'))
                self.logger.info('Downloading from remote repository...')
                await self.bot.loop.run_in_executor(None, lambda: os.system(
                    'git clone --branch ' + version + ' --single-branch --depth 1 ' + self.bot.config[
                        'files_endpoint'] + '/unifier.git update'
                ))
                self.logger.debug('Confirming download...')
                x = open(os.getcwd() + '/update/plugins/system.json', 'r')
                x.close()
                self.logger.debug('Download confirmed, proceeding with upgrade')
            except:
                self.logger.exception('Download failed, no rollback required')
                embed.title = f'{self.bot.ui_emojis.error} {selector.get("failed")}'
                embed.description = selector.get("download_fail")
                embed.colour = self.bot.colors.error
                await msg.edit(embed=embed)
                return
            try:
                self.logger.debug('Installing dependencies')

                with open('.install.json') as file:
                    install_data = json.load(file)

                if install_data == 'stable':
                    x = open('update/requirements_stable.txt')
                    newdeps = x.read().split('\n')
                    x.close()
                else:
                    x = open('update/requirements.txt')
                    newdeps = x.read().split('\n')
                    x.close()

                try:
                    if install_data == 'stable':
                        x = open('requirements_stable.txt')
                        olddeps = x.read().split('\n')
                        x.close()
                    else:
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
                    bootloader_config = self.bot.boot_config.get('bootloader', {})
                    if sys.platform == 'win32':
                        binary = bootloader_config.get('binary', 'py -3')
                        await self.bot.loop.run_in_executor(None, lambda: status(
                            os.system(f'{binary} -m pip install -U ' + '"' + '" "'.join(newdeps) + '"')
                        ))
                    else:
                        binary = bootloader_config.get('binary', 'python3')
                        await self.bot.loop.run_in_executor(None, lambda: status(
                            os.system(f'{binary} -m pip install -U ' + '"' + '" "'.join(newdeps) + '"')
                        ))
            except:
                self.logger.exception('Dependency installation failed, no rollback required')
                embed.title = f'{self.bot.ui_emojis.error} {selector.get("failed")}'
                embed.description = selector.get("dependency_fail")
                embed.colour = self.bot.colors.error
                await msg.edit(embed=embed)
                return
            try:
                self.logger.info('Installing upgrades')
                embed.description = f':white_check_mark: {selector.get("downloading")}\n:hourglass_flowing_sand: {selector.get("installing")}\n:x: {selector.get("reloading")}'
                await msg.edit(embed=embed)
                self.logger.debug('Installing: ' + os.getcwd() + '/update/unifier.py')
                await self.copy('update/unifier.py', 'unifier.py')
                self.logger.debug('Installing: ' + os.getcwd() + '/update/requirements.txt')
                await self.copy('update/requirements.txt', 'requirements.txt')
                self.logger.debug('Installing: ' + os.getcwd() + '/update/requirements_stable.txt')
                await self.copy('update/requirements_stable.txt', 'requirements_stable.txt')
                self.logger.debug('Installing: ' + os.getcwd() + '/update_check/plugins/system.json')
                if legacy:
                    current['version'] = version
                    current['legacy'] = release
                    with open('plugins/system.json', 'w+') as file:
                        json.dump(current,file)
                else:
                    await self.copy('update/plugins/system.json', 'plugins/system.json')
                for file in os.listdir(os.getcwd() + '/update/cogs'):
                    self.logger.debug('Installing: ' + os.getcwd() + '/update/cogs/' + file)
                    await self.copy('update/cogs/' + file, 'cogs/' + file)
                for file in os.listdir(os.getcwd() + '/update/utils'):
                    self.logger.debug('Installing: ' + os.getcwd() + '/update/utils/' + file)
                    await self.copy('update/utils/' + file, 'utils/' + file)
                self.logger.debug('Installing: ' + os.getcwd() + '/update/emojis/base.json')
                await self.copy('update/emojis/base.json', 'emojis/base.json')
                self.logger.debug('Updating languages')
                for file in os.listdir(os.getcwd() + '/update/languages'):
                    if not file.endswith('.json'):
                        continue

                    self.logger.debug('Installing: ' + os.getcwd() + '/update/languages/' + file)
                    await self.copy('update/languages/' + file, 'languages/' + file)
                for file in os.listdir(os.getcwd() + '/update/utils'):
                    self.logger.debug('Installing: ' + os.getcwd() + '/update/utils/' + file)
                    await self.copy('update/utils/' + file, 'utils/' + file)
                self.logger.debug('Updating config.toml')
                with open('config.toml','rb') as file:
                    oldcfg = tomli.load(file)
                with open('update/config.toml', 'rb') as file:
                    newcfg = tomli.load(file)

                newdata = {}

                for key in oldcfg:
                    if type(oldcfg[key]) is dict:
                        for newkey in oldcfg[key]:
                            newdata.update({newkey: oldcfg[key][newkey]})
                    else:
                        newdata.update({key: oldcfg[key]})

                oldcfg = newdata

                def update_toml(old, new):
                    for key in new:
                        for newkey in new[key]:
                            if newkey in old.keys():
                                new[key].update({newkey: old[newkey]})
                    return new

                oldcfg = update_toml(oldcfg, newcfg)

                with open('config.toml', 'wb+') as file:
                    tomli_w.dump(oldcfg, file)
                if should_reboot:
                    self.bot.update = True
                    self.logger.info('Upgrade complete, reboot required')
                    embed.title = f'{self.bot.ui_emojis.success} {selector.get("restart_title")}'
                    embed.description =selector.get("restart_body")
                    embed.colour = self.bot.colors.success
                    await msg.edit(embed=embed)
                else:
                    self.logger.info('Reloading extensions')
                    f':white_check_mark: {selector.get("downloading")}\n:white_check_mark: {selector.get("installing")}\n:hourglass_flowing_sand: {selector.get("reloading")}'
                    await msg.edit(embed=embed)
                    for cog in list(self.bot.extensions):
                        self.logger.debug('Reloading extension: ' + cog)
                        try:
                            await self.preunload(cog)
                            self.bot.reload_extension(cog)
                        except:
                            self.logger.warning(cog+' could not be reloaded.')
                            embed.set_footer(text=':warning: Some extensions could not be reloaded.')
                    self.logger.info('Upgrade complete')
                    embed.title = f'{self.bot.ui_emojis.success} {selector.get("success_title")}'
                    embed.description = selector.get("success_body")
                    embed.colour = self.bot.colors.success
                    await msg.edit(embed=embed)
            except:
                self.logger.exception('Upgrade failed, attempting rollback')
                embed.title = f'{self.bot.ui_emojis.error} {selector.get("failed")}'
                embed.colour = self.bot.colors.error
                try:
                    self.logger.debug('Reverting: ' + os.getcwd() + '/unifier.py')
                    await self.copy('old/unifier.py', 'unifier.py')
                    self.logger.debug('Reverting: ' + os.getcwd() + '/data.json')
                    await self.copy('old/data.json', 'data.json')
                    self.logger.debug('Reverting: ' + os.getcwd() + '/plugins/system.json')
                    await self.copy('old/plugins/system.json', 'plugins/system.json')
                    self.logger.debug('Reverting: ' + os.getcwd() + '/config.toml')
                    await self.copy('old/config.toml', 'config.toml')
                    for file in os.listdir(os.getcwd() + '/old/cogs'):
                        self.logger.debug('Reverting: ' + os.getcwd() + '/cogs/' + file)
                        await self.copy('old/cogs/' + file, 'cogs/' + file)
                    self.logger.info('Rollback success')
                    embed.description = selector.get("rollback")
                except:
                    self.logger.exception('Rollback failed')
                    self.logger.critical(
                        'The rollback failed. Visit https://unichat-wiki.pixels.onl/setup-selfhosted/upgrading-unifier/manual-rollback for recovery steps.')
                    embed.description = selector.get("rollback_fail")
                await msg.edit(embed=embed)
                return
        else:
            embed = nextcord.Embed(title=f'{self.bot.ui_emojis.install} {selector.rawget("downloading_title","sysmgr.install")}', description=selector.rawget("downloading_body",'sysmgr.install'))

            try:
                with open('plugins/'+plugin+'.json') as file:
                    plugin_info = json.load(file)
            except:
                embed.title = f'{self.bot.ui_emojis.error} {selector.get("notfound_title")}'
                embed.description = selector.get("notfound_body")
                if plugin=='force':
                    embed.description = embed.description + '\n' + selector.fget('hint_force',values={'prefix':self.bot.command_prefix})
                embed.colour = self.bot.colors.error
                await ctx.send(embed=embed)
                return
            embed.set_footer(text=selector.rawget("trust",'sysmgr.install'))
            msg = await ctx.send(embed=embed)
            url = plugin_info['repository']
            try:
                await self.bot.loop.run_in_executor(None, lambda: shutil.rmtree('plugin_install'))
                await self.bot.loop.run_in_executor(None, lambda: status(os.system(
                    'git clone ' + url + ' plugin_install')))
                with open('plugin_install/plugin.json', 'r') as file:
                    new = json.load(file)
                if not bool(re.match("^[a-z0-9_-]*$", new['id'])):
                    embed.title = f'{self.bot.ui_emojis.error} {selector.rawget("alphanumeric_title","sysmgr.install")}'
                    embed.description = selector.rawget("alphanumeric_body",'sysmgr.install')
                    embed.colour = self.bot.colors.error
                    await msg.edit(embed=embed)
                    return
                if new['release'] <= plugin_info['release'] and not force:
                    embed.title = f'{self.bot.ui_emojis.success} {selector.get("pnoupdates_title")}'
                    embed.description = selector.get("pnoupdates_body")
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
                embed.title = f'{self.bot.ui_emojis.error} {selector.get("pfailed")}'
                embed.description = selector.rawget("invalid_repo",'sysmgr.install')
                embed.colour = self.bot.colors.error
                await msg.edit(embed=embed)
                raise
            embed.title = f'{self.bot.ui_emojis.install} {selector.fget("question",values={"plugin":plugin_id})}'
            embed.description = selector.rawfget('plugin_info','sysmgr.install',values={'name':name,'version':version,'desc':desc})
            embed.colour = 0xffcc00
            btns = ui.ActionRow(
                nextcord.ui.Button(style=nextcord.ButtonStyle.green, label=selector.get("upgrade"), custom_id=f'accept', disabled=False),
                nextcord.ui.Button(style=nextcord.ButtonStyle.gray, label=selector.rawfget("nevermind","sysmgr.install"), custom_id=f'reject', disabled=False)
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
                            bootloader_config = self.bot.boot_config.get('bootloader', {})
                            if sys.platform == 'win32':
                                binary = bootloader_config.get('binary', 'py -3')
                                await self.bot.loop.run_in_executor(None, lambda: status(
                                    os.system(f'{binary} -m pip install --no-dependencies -U ' + '"' + '" "'.join(newdeps) + '"')
                                ))
                            else:
                                binary = bootloader_config.get('binary', 'python3')
                                await self.bot.loop.run_in_executor(None, lambda: status(
                                    os.system(f'{binary} -m pip install --no-dependencies -U ' + '"' + '" "'.join(newdeps) + '"')
                                ))
                except:
                    self.logger.exception('Dependency installation failed')
                    raise RuntimeError()
                self.logger.info('Upgrading Plugin')
                for module in modules:
                    self.logger.debug('Installing: ' + os.getcwd() + '/plugin_install/' + module)
                    await self.copy('plugin_install/' + module, 'cogs/' + module)
                for util in utilities:
                    self.logger.debug('Installing: ' + os.getcwd() + '/plugin_install/' + util)
                    await self.copy('plugin_install/' + util, 'utils/' + util)
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

                if not os.path.exists('plugin_config'):
                    os.mkdir('plugin_config')

                if 'config.toml' in os.listdir('plugin_install'):
                    if f'{plugin_id}.toml' in os.listdir('plugin_config'):
                        self.logger.debug('Updating config.toml')
                        with open(f'plugin_config/{plugin_id}.toml', 'rb') as file:
                            oldcfg = tomli.load(file)
                        with open('plugin_install/config.toml', 'rb') as file:
                            newcfg = tomli.load(file)

                        newdata = {}

                        for key in oldcfg:
                            if type(oldcfg[key]) is dict:
                                for newkey in oldcfg[key]:
                                    newdata.update({newkey: oldcfg[key][newkey]})
                            else:
                                newdata.update({key: oldcfg[key]})

                        oldcfg = newdata

                        def update_toml(old, new):
                            for key in new:
                                for newkey in new[key]:
                                    if newkey in old.keys():
                                        new[key].update({newkey: old[newkey]})
                            return new

                        oldcfg = update_toml(oldcfg, newcfg)

                        with open(f'plugin_config/{plugin_id}.toml', 'wb+') as file:
                            tomli_w.dump(oldcfg, file)
                    else:
                        self.logger.debug('Installing config.toml')
                        if not os.path.exists('plugin_config'):
                            os.mkdir('plugin_config')
                        await self.copy('plugin_install/config.toml', 'plugin_config/' + plugin_id + '.toml')

                self.logger.info('Registering plugin')
                await self.copy('plugin_install/plugin.json', 'plugins/' + plugin_id + '.json')
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
                        try:
                            await self.preunload(modname)
                            self.bot.reload_extension(modname)
                        except:
                            self.logger.warning(modname+' could not be reloaded.')
                            embed.set_footer(text=':warning: Some extensions could not be reloaded.')
                self.logger.debug('Upgrade complete')
                embed.title = f'{self.bot.ui_emojis.success} {selector.get("success_title")}'
                embed.description = selector.get("success_body")

                if 'bridge_platform' in plugin_info['services']:
                    embed.description = embed.description + '\n' + selector.get('success_rpossible')

                embed.colour = self.bot.colors.success
                await msg.edit(embed=embed)
            except:
                self.logger.exception('Upgrade failed')
                embed.title = f'{self.bot.ui_emojis.error} {selector.get("failed")}'
                embed.description = selector.get("plugin_fail")
                embed.colour = self.bot.colors.error
                await msg.edit(embed=embed)
                return

def setup(bot):
    bot.add_cog(EmergencyUpgrader(bot))
