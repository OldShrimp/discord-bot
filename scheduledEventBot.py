import discord
from discord.ext import tasks, commands
import json

class MyClient(discord.Client):
    def __init__(self, *, intents, **options):
        super().__init__(intents=intents, **options)
        # {guild.id:{event.id:role.id}}
        self.managed_events = {}
        
    async def on_ready(self):
            print(f'We have logged in as {self.user}')
            for guild in self.guilds:
                self.managed_events[guild] = {}
                for events in guild.scheduled_events:
                    self.managed_events[guild]
                    for role in guild.roles:
                        print(role.name, role.tags)
                        if role.is_bot_managed() and role.tags.bot_id == self.user.id:
                            pass
            
    def make_role_name(self, event: discord.ScheduledEvent):
        role_name = event.name
        if role_name[-1] == "y" and role_name[-2] not in ["a", "e", "i", "o", "u"]:
            role_name = role_name[:-1] + "i"
        return role_name + "ers"
    
    def find_role(self, event: discord.ScheduledEvent):
        role_name = self.make_role_name(event)
        for role in event.guild.roles:
            if role.name == role_name:
                return role
        return None
    
    async def create_event_role(self, event: discord.ScheduledEvent):
        role = await event.guild.create_role(name=self.make_role_name(event), mentionable=True, reason="event created")
        self.managed_events[event.guild.id][event.id] = role.id
        async for user in event.users():
            await event.guild.get_member(user.id).add_roles(role)
    
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        print(f'Event {event.name} created.')
        #if self.find_role(event):
         #   await event.edit(name=event.name + " event", reason="event name conflicted with preexisting roles")
        await self.create_event_role(event=event)
    
    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        print(f'Event {event.name} deleted.')
        if self.managed_events[event.guild.id][event.id]:
            await self.managed_events[event.guild.id][event.id].delete(reason="event ended or cancelled, corresponding role deleted")
    
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        print(f'Event {before.name} updated.')
        if before.name != after.name:
            await self.managed_events[before.guild.id][before.id].edit(name=self.make_role_name(after))
    
    async def on_scheduled_event_user_add(self, event: discord.ScheduledEvent, user: discord.User):
        print(f'User {user} added to event {event.name}.')
        role = self.managed_events[event.guild.id][event.id]
        if role and event.guild.get_member(user.id):
            await event.guild.get_member(user.id).add_roles(role)
    
    async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent, user: discord.User):
        print(f'User {user} removed from event {event.name}.')
        role = self.managed_events[event.guild.id][event.id]
        if role and event.guild.get_member(user.id):
            await event.guild.get_member(user.id).remove_roles(role)

if __name__ == "__main__":
    intents = discord.Intents.all()
    client = MyClient(intents=intents)
    with open('token.txt') as token_file:
        client.run(token_file.read())