import time
import random
import datetime as dt
import telepot
import sys
import os
from telepot.loop import MessageLoop
import netifaces as ni
import vlc
import pafy

"""
pybot for telegram control
"""
player = None
list_player = None
playlist = None
instance = None

def start_player():
    global player, instance
    instance = vlc.Instance('--play-and-exit', '--fullscreen')
    player = instance.media_player_new()
    player.set_fullscreen(True)
    player.audio_set_mute(False)

def start_playlist():
    global instance, playlist, list_player
    playlist = instance.media_list_new()
    list_player = instance.media_list_player_new()
    list_player.set_media_list(playlist)
    list_player.set_media_player(player)

def add_video(video):
    global instance, playlist
    best = video.getbest()
    playlist.add_media(instance.media_new(best.url))

def handle(msg):
    global player, list_player, instance
    chat_id = msg['chat']['id']
    command = msg['text']

    # print('Got command: %s' % command)

    if command == 'commands':
        answer = ''
        answer += 'ip'
        answer += '\n'
        answer += 'uptime'
        answer += '\n'
        answer += '<youtube URL to attach to playlist>'
        answer += '\n'
        answer += 'yt add URL>'
        answer += '\n'
        answer += 'yt play <URL>'
        answer += '\n'
        answer += 'yt playlist <playlist URL>'
        answer += '\n'
        answer += 'yt mute'
        answer += '\n'
        answer += 'yt next'
        answer += '\n'
        answer += 'yt pause'
        answer += '\n'
        answer += 'yt close'
        answer += '\n'
        answer += 'yt source'
        answer += '\n'
        answer += 'yt previous'
        bot.sendMessage(chat_id, answer)
    
    elif command == 'ip':
        ip6 = ni.ifaddresses('wlx24050fa8674d')[10][0]['addr']
        bot.sendMessage(chat_id, str(ip6))

#    if command == 'status':
#       status=`dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 or$
    
    elif command == "uptime":
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(dt.timedelta(seconds = uptime_seconds))
            bot.sendMessage(chat_id, uptime_string[:-7])
    
    elif command[:2] == 'yt':
        if len(command) > 4:
            com = command[3:]
            
            if com[:3] == 'add':
                url = com[4:]
                if instance == None:
                    start_player()
                    start_playlist()
                video = pafy.new(url)
                add_video(video)
                list_player.play()
                
            elif com[:8] == 'playlist':
                print(com[9:])
                try:
                    for video in pafy.get_playlist(com[9:])['items']:
                        if instance == None:
                            start_player()
                            start_playlist()
                        add_video(video['pafy'])
                        list_player.play()
                except ValueError as v:
                    bot.sendMessage(chat_id, str(v))


            elif com[:4] == 'play':
                #stop pausing
                if len(com) == 4:
                    if instance != None:
                        player.set_pause(False)
                    return
                #play url
                start_player()
                start_playlist()
                url = com[5:]
                video = pafy.new(url)
                add_video(video)
                list_player.play()

                
            elif com[:4] == 'mute':
                if instance != None:
                    player.audio_toggle_mute()
            
            elif com[:4] == 'next':
                list_player.next()

            elif com[:5] == 'pause':
                #toggle pause
                if instance != None:
                    player.pause()

            elif com[:5] == 'close':
                if instance != None:
                    player.stop()

            elif com[:6] == 'source':
                if instance == None:
                    bot.sendMessage(chat_id, 'Nothing is playing at the moment.')
                else:
                    title = player.get_media().get_mrl()
                    bot.sendMessage(chat_id, title)
    

            elif com[:8] == 'previous':
                list_player.previous()

    else:
        for com in command.split():
            if com[:4] == 'http':
                try:
                    video = pafy.new(com)
                    if instance == None:
                        start_player()
                        start_playlist()
                    add_video(video)
                    list_player.play()
                    return

                except ValueError as v:
                    bot.sendMessage(chat_id, str(v))
                    return
        bot.sendMessage(chat_id, 'command unknown')

bot = telepot.Bot('')
MessageLoop(bot, handle).run_as_thread()
print('I am listening ...')

while 1:
    time.sleep(10)
