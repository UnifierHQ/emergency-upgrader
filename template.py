"""
<one line to give the program's name and a brief idea of what it does.>
Copyright (C) <year>  <name of author>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import discord
from discord.ext import commands

class Template(commands.Cog):
    """A template cog written for unifier-plugin temmplate repo"""
    
    def __init__(self,bot):
        self.bot = bot

    @commands.command()
    async def template(self,ctx):
        await ctx.send('This is a template plugin!')

def setup(bot):
    bot.add_cog(Template(bot))
