import time
import threading
import datetime as dt
from tkinter import NO
import telepot
import os
from telepot.loop import MessageLoop
import netifaces as ni
import vlc
from pytube import YouTube, exceptions as yt_exceptions
import alsaaudio
import shutil

video_path = '/tmp/videos'

"""
pybot for telegram control
"""
player = None
list_player = None
playlist = None
instance = None
download_size = 0
percentage_print_counter = 0
callback_chat_id = 0
mutex = threading.Lock()

def ip():
    return ni.ifaddresses('wlan0')[10][0]['addr']

def uptime():
    with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(dt.timedelta(seconds = uptime_seconds))
            return uptime_string[:-7]

def get_volume():
    return str(alsaaudio.Mixer().getvolume()[0]) + '%'

def volume(command):
    if command != "":
        try:
            vol = int(command)
            if vol >= 0 and vol <= 100:
                alsaaudio.Mixer().setvolume(vol)
        except ValueError:
            return 'Volume change not possible. stuck on: ' + get_volume()

    return get_volume()

def vlc_volume(command):
    global player
    if instance == None:
        return "Player not instantiated"
    if command != "":
        try:
            vol = int(command)
            if vol >= 0 and vol <= 100:
                player.audio_set_volume(vol)
        except ValueError:
            return 'Volume change not possible. stuck on: ' + player.audio_get_volume()
    # time to make the adjustment in vlc
    time.sleep(0.1)
    return player.audio_get_volume()

def lower_string(commands):
    command = ''
    for com in commands.split():
        if com[:4] == 'http':
            command += com + ' '
        else:
            command += com.lower() + ' '
    return command[:-1]

def commands():
    answer = 'commands #show available commands'
    answer +='\n'
    answer += 'ip'
    answer += '\n'
    answer += 'uptime'
    answer += '\n'
    answer += 'volume (<%>) #request / set volume'
    answer += '\n'
    answer += 'vlc volume (<%>) #request / set volume in vlc player'
    answer += '\n'
    answer += 'play all #play everything cached'
    answer += '\n'
    answer += 'pause'
    answer += '\n'
    answer += 'stop #end player'
    answer += '\n'
    answer += 'mute'
    answer += '\n'
    answer += 'clear #clear all chached somgs'
    answer += '\n'
    answer += 'next'
    answer += '\n'
    answer += 'previous'
    answer += '\n'
    answer += 'playlist #show cached songs'
    answer += '\n'
    answer += '<youtube url> #play song from youtube'
    answer += '\n'
    answer += 'add <youtube url> #add song to end of playlist'
    return answer

# preprare vlc
def start_player():
    global player, instance
    instance = vlc.Instance('--play-and-exit', '--fullscreen')
    player = instance.media_player_new()
    player.set_fullscreen(True)
    player.audio_set_mute(False)

# prepare vlc playlist, needs prepared player
def start_playlist():
    global instance, playlist, list_player
    playlist = instance.media_list_new()
    list_player = instance.media_list_player_new()
    list_player.set_media_list(playlist)
    list_player.set_media_player(player)





def download_callback(stream, chunks, bytes_remaining):
    global download_size, percentage_print_counter
    if download_size == 0:
        download_size = bytes_remaining
    percentage = 1 - bytes_remaining/(download_size+0.1)
    if percentage_print_counter == 0 and percentage >= 0.25 and percentage < 0.75:
        bot.sendMessage(callback_chat_id, "downloaded 25%")
        percentage_print_counter = 1
    if percentage_print_counter == 1 and percentage >= 0.5:
        bot.sendMessage(callback_chat_id, "downloaded 50%")
        percentage_print_counter = 2
    if percentage_print_counter == 2 and percentage >= 0.75:
        bot.sendMessage(callback_chat_id, "downloaded 75%")
        percentage_print_counter = 0

def previous_video(chat_id):
    global list_player
    if instance is not None:
        list_player.previous()
    else:
        bot.sendMessage(chat_id, "nothing is playing")


def playing(chat_id):
    global instance, player
    if instance == None:
        bot.sendMessage(chat_id, "Nothing is playing at the moment.")
    else:
        print(player.video_get_title_description())
        bot.sendMessage(chat_id, "youtube is playing")

def pause(chat_id):
    global instance, player
    #toggle pause
    if instance != None:
        player.pause()
        bot.sendMessage(chat_id, "Pause toggled")
    else:
        bot.sendMessage(chat_id, "Nothing is playing at the moment.")

def end():
    global instance, player, playlist
    if instance != None:
        player.stop()
        instance = player = playlist = None

def play_all(chat_id):
    global instance, player, playlist
    end()
    start_player()
    start_playlist()
    try:
        for video in os.listdir(video_path+"/"):
            abs_path = video_path + "/" + video
            playlist.add_media(abs_path)
    except FileNotFoundError:
        pass
    if playlist.count() > 0:
        list_player.play()
        bot.sendMessage(chat_id, "playing")
    else:
        bot.sendMessage(chat_id, "nothing to play")

def close(chat_id):
    global instance, player, playlist
    if instance != None:
        end()
        bot.sendMessage(chat_id, "closed")
    else:
        bot.sendMessage(chat_id, "wasn\'t running")

def clear(chat_id):
    global player, instance
    end()
    try:
        shutil.rmtree(video_path)
        bot.sendMessage(chat_id, "videos have been cleared")
    except FileNotFoundError:
        bot.sendMessage(chat_id, "nothing to clear")


def mute(chat_id):
    global instance, player
    if instance != None:
        player.audio_toggle_mute()
        bot.sendMessage(chat_id, "mute toggled")

    else:
        bot.sendMessage(chat_id, "nothing is playing")

def next_video(chat_id):
    global list_player
    if instance is not None:
        list_player.next()
        bot.sendMessage(chat_id, "next song")
    else:
        bot.sendMessage(chat_id, "nothing is playing")

def previous_video(chat_id):
    global list_player
    if instance is not None:
        list_player.previous()
        bot.sendMessage(chat_id, "previous song")
    else:
        bot.sendMessage(chat_id, "nothing is playing")

def show_playlist(chat_id):
    global list_player, instance
    try:
        for item in os.listdir(video_path+"/"):
            bot.sendMessage(chat_id, item)
    except:
        bot.sendMessage(chat_id, "nothing to play")



# add video to playlist, print Volume as prove of reception
def add_video(yt, restart, chat_id):
    global playlist, callback_chat_id
    bot.sendMessage(chat_id, 'trying to initiate download')
    yt.register_on_progress_callback(download_callback)
    callback_chat_id = chat_id
    file_path = ""
    try:
        file_path = yt.streams.filter(abr="128kbps").first().download(video_path)
    except (SyntaxError, yt_exceptions.RegexMatchError):
        bot.sendMessage(chat_id, 'command not recognized/Video not found')
        callback_chat_id = 0
        return
    print("playlist", playlist)
    if restart:
        end()
        start_player()
        start_playlist()
    print(playlist)
    playlist.add_media(file_path)
    list_player.play()
    bot.sendMessage(chat_id, 'download finished')
    callback_chat_id = 0
    return



def handle(msg):
    global player, list_player, instance, mutex
    chat_id = msg['chat']['id']
    command = lower_string(msg['text'])

    print('Got command: %s' % command)

    if command == 'commands':
        bot.sendMessage(chat_id, commands())
    
    elif command == 'ip':
        bot.sendMessage(chat_id, ip())

    
    elif command == "uptime":
        bot.sendMessage(chat_id, uptime())

    elif command[:6] == 'volume':
        bot.sendMessage(chat_id, volume(command[7:]))

    elif command[:10] == 'vlc volume':
        bot.sendMessage(chat_id, vlc_volume(command[11:]))

    else:
        mutex.acquire()

        if command == 'play all':
            play_all(chat_id)

        elif command == 'pause':
            pause(chat_id)

        elif command == 'stop':
            close(chat_id)

        elif command == 'mute':
            mute(chat_id)

        elif command == 'clear':
            clear(chat_id)

        elif command == 'next':
            next_video(chat_id)

        elif command == 'previous':
            previous_video(chat_id)

        elif command == 'playing':
            playing(chat_id)
            
        elif command == 'playlist':
            show_playlist(chat_id)

        elif command[:4] == 'add ':
            yt= None
            try:
                yt = YouTube(command[4:])
                yt.check_availability()

            except yt_exceptions.RegexMatchError:
                bot.sendMessage(chat_id, "could not parse that...")
                mutex.release()
                return
            add_video(yt, False,chat_id)

        else:
            yt= None
            try:
                yt = YouTube(command)
                yt.check_availability()

            except yt_exceptions.RegexMatchError:
                bot.sendMessage(chat_id, "could not parse that...")
                mutex.release()
                return
            except yt_exceptions.LiveStreamError:
                bot.sendMessage(chat_id, "can not play live streams")
                mutex.release()
                return

            add_video(yt, True, chat_id)
        mutex.release()

    #VLC related ends(mutex)

bot = telepot.Bot('...')
MessageLoop(bot, handle).run_as_thread()
print('I am listening ...')

while 1:
    time.sleep(10)

