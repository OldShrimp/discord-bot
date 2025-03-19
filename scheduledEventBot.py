import discord
import sqlite3


class MyClient(discord.Client):
    def __init__(self, *, intents, **options):
        super().__init__(intents=intents, **options)
        
        self.database = sqlite3.connect("discord_events.db")
        self.database.execute("CREATE TABLE IF NOT EXISTS guilds(guild_id INT UNIQUE, guild_name TEXT, PRIMARY KEY (guild_id))")
        self.database.execute("CREATE TABLE IF NOT EXISTS scheduled_events(guild_id INT, event_id INT, event_name TEXT, role_id INT, PRIMARY KEY (guild_id, event_id))")
        
    async def on_ready(self):
            print(f'We have logged in as {self.user}')
            for guild in self.guilds:
                self.database.execute("""INSERT INTO guilds(guild_id, guild_name)
                                         VALUES(?, ?)
                                         ON CONFLICT(guild_id) 
                                         DO UPDATE SET guild_name=excluded.guild_name""", 
                                         (guild.id, guild.name))
                self.database.commit()
                for event in guild.scheduled_events:
                    if self.query_event(event=event) == None:
                        new_role = await self.create_event_role(event=event)
                        self.database.execute("""INSERT INTO scheduled_events(guild_id, event_id, event_name, role_id) 
                                                 VALUES(?, ?, ?, ?)""", 
                                                 (guild.id, event.id, event.name, new_role.id))
                        self.database.commit()
    
    def query_event(self, event:discord.ScheduledEvent):
        return self.database.execute("""SELECT *
                                        FROM scheduled_events
                                        WHERE guild_id = ? AND event_id = ?""",
                                        (event.guild.id, event.id)
                                    ).fetchone()
    
    async def add_event(self, event:discord.ScheduledEvent):
        new_role = await self.create_event_role(event=event)
        self.database.execute("""INSERT INTO scheduled_events (guild_id, event_id, event_name, role_id) 
                                 VALUES(?, ?, ?, ?)""", 
                                 (event.guild.id, event.id, event.name, new_role.id))
        self.database.commit()
        
    async def remove_event(self, event:discord.ScheduledEvent):
        await event.guild.get_role(self.query_event(event=event)[3]).delete(reason=f"event {event.name} ended or cancelled, corresponding role deleted")
        self.database.execute("""DELETE FROM scheduled_events
                                    WHERE guild_id = ? AND event_id = ?""",
                                    (event.guild.id, event.id))
        self.database.commit()

    def make_role_name(self, event: discord.ScheduledEvent):
        role_name = event.name
        if len(role_name) > 1 and role_name[-1] == "y" and role_name[-2] not in ["a", "e", "i", "o", "u"]:
            role_name = role_name[:-1] + "i"
        return role_name + "ers"

    async def create_event_role(self, event: discord.ScheduledEvent) -> discord.Role:
        role = await event.guild.create_role(name=self.make_role_name(event), mentionable=True, reason=f"event {event.name} created")
        async for user in event.users():
            await event.guild.get_member(user.id).add_roles(role)
        return role
    
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        print(f'Event {event.name} created.')
        await self.add_event(event=event)
    
    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        print(f'Event {event.name} deleted.')
        event_data = self.query_event(event=event)
        if event_data == None:
            print("event was untracked")
        elif event.guild.get_role(event_data[3]) != None:
            await self.remove_event(event=event)
    
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        print(f'Event {before.name} updated to {after.name}.')
        if after.status == discord.EventStatus.completed or after.status == discord.EventStatus.cancelled:
            print(f'Event {after.name} ended or cancelled.')
            await self.remove_event(event=after)
        elif before.name != after.name:
            event_data = self.query_event(event=after)
            await after.guild.get_role(event_data[3]).edit(name=self.make_role_name(after))
            self.database.execute("""UPDATE scheduled_events
                                     SET event_name = ?
                                     WHERE guild_id = ? AND event_id = ?""",
                                     (after.name, after.guild.id, after.id))
            self.database.commit()
    
    async def on_scheduled_event_user_add(self, event: discord.ScheduledEvent, user: discord.User):
        print(f'User {user} added to event {event.name}.')
        event_data = self.query_event(event=event)
        if event_data != None and event.guild.get_member(user.id) and event.guild.get_role(event_data[3]) != None:
            await event.guild.get_member(user.id).add_roles(event.guild.get_role(event_data[3]))
    
    async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent, user: discord.User):
        print(f'User {user} removed from event {event.name}.')
        event_data = self.query_event(event=event)
        if event_data != None and event.guild.get_member(user.id) and event.guild.get_role(event_data[3]) != None:
            await event.guild.get_member(user.id).remove_roles(event.guild.get_role(event_data[3]))

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.members = True
    client = MyClient(intents=intents)
    with open('token.txt') as token_file:
        client.run(token_file.read())