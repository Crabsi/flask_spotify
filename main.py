from flask import Flask, render_template, redirect, request, session, make_response, session, redirect, url_for, jsonify
import requests
import json
import os

app = Flask(__name__)

CLI_ID = os.environ.get('FLASK_CLIENT_ID')
CLI_SEC = os.environ.get('FLASK_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('FLASK_REDIRECT_URI')
app.secret_key = os.environ.get('FLASK_APP_KEY')

API_BASE = 'https://accounts.spotify.com'

SCOPE = 'playlist-modify-private,playlist-modify-public,user-top-read,user-read-private,user-read-email,playlist-read-private,playlist-read-collaborative'

# Set this to True for testing but you probably want it set to False in production.
SHOW_DIALOG = True



@app.route("/")
# root funtion
# redirect to login_page function
def root():
    if session.get('toke') == None:
        return redirect("login_page")
    else:
        return redirect("index")


@app.route("/login_page", methods=['GET', 'POST'])
# login_page function
# renders login_page.html
def login_page():
    return render_template("login_page.html")


@app.route("/sign_in", methods=['GET', 'POST'])
# sign in function
# creates authentication url for auth request to spotify
# redirects to the auth_url
def verify():
    auth_url = f'{API_BASE}/authorize?client_id={CLI_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}&show_dialog={SHOW_DIALOG}'
    return redirect(auth_url)


@app.route("/api_callback")
# api_callback function
# makes request to spotify web API to get a token for authentication
# redirects to index function
def api_callback():
    session.clear()
    code = request.args.get('code')
    auth_token_url = f"{API_BASE}/api/token"

    # Make token request
    res = requests.post(auth_token_url, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLI_ID,
        "client_secret": CLI_SEC
    })

    # Save token in variable "toke" and store it for the session
    res_body = res.json()
    session["toke"] = res_body.get("access_token")
    return redirect("index")


@app.route("/index", methods=['GET', 'POST'])
# index function
# renders index.html
def index():
    # Create request header for the session
    token = session.get('toke')
    session['headers'] = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }

    # Get User ID
    result_get_id = requests.get(
        'https://api.spotify.com/v1/me', headers=session.get('headers'))
    json_result_get_id = result_get_id.json()
    session['user_id'] = json_result_get_id['id']

    return render_template('index.html')


@app.route('/playlist_index')
# playlist_index function
# calls function to get all of the users playlist and returns the values to the playlist_index.html
# renders playlist_index.html
def playlist_index():
    # call function to get all playlists
    get_all_playlists()

    # get the data from the session
    playlist_amount_user = session.get("playlist_amount_user")
    playlist_name_list = session.get("playlist_name_list")
    playlist_id_list = session.get("playlist_id_list")

    # Get the argument "playlist_error"
    playlist_error = request.args.get('playlist_error')

    return render_template("playlist_index.html",
                           playlist_id_list=playlist_id_list,
                           playlist_name_list=playlist_name_list,
                           playlist_amount=playlist_amount_user,
                           playlist_error=playlist_error)


@app.route('/select_playlist', methods=['GET', 'POST'])
# select_playlist function
# after selecting a playlist in the playlist_index, this function needs to get the argument of the chosen playlist
# renders search_album.html
def select_playlist():
    # Get index_number from URL
    playlist_number = request.args.get('playlist_number')
    playlist_id_list = session.get('playlist_id_list')
    session['playlist_id'] = playlist_id_list[int(playlist_number)]

    return redirect("search_album")


@app.route('/create_playlist', methods=['GET', 'POST'])
# create_playlist function
# creates a new playlist with a given name
# redirects to search_album function
def create_playlist():
    # Define data for request
    a = '{'
    name = request.form['new_playlist_name']
    false = 'false'
    b = '}'

    # If no name is entered into the "Playlist Name" form, set the argument "playlist_error" = 1
    if name == "":
        return redirect(url_for('playlist_index', playlist_error='1'))

    # If a name is entered, create the playlist with the given name
    else:
        session['data_create_playlist'] = f'{a}"name":"{name}","description":"Platzhalter Beschreibung","public":{false}{b}'

        # call function to create playlist
        create_new_playlist()

        return redirect("/search_album")


@app.route('/search_album', methods=['GET', 'POST'])
# search_album function
# renders search_album.html
def search_album():
    return render_template("/search_album.html")


@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    album_form = request.args.get('q')
    if len(album_form) >= 3:
        album = album_form
        params_search_album = (
            ('q', album),
            ('type', 'album'),
            ('limit', '5'),
            ('offset', '0'),
        )

        result_search_album = requests.get(
            'https://api.spotify.com/v1/search', headers=session.get('headers'), params=params_search_album)
        result_search_album_json = result_search_album.json()

        album_info = {}
        album_info['album'] = []
        album_name_list = []
        for index, album in enumerate(result_search_album_json['albums']['items']):
            album_info['album'].append({
                "album_name": album['name'],
                "album_id": str(album['id'])
            })
            album_name = album['name']
            album_artist = album['artists'][0]['name']
            album_name_list.append(f'{album_name} | {album_artist}')

        return jsonify(albums=album_name_list)

    else:
        return redirect('/search_album')


@app.route('/find_album', methods=['GET', 'POST'])
# find_album function
# makes a request to the web API to find an album and get some data of it
# redirects to add_songs function
def find_album():
    # Define parameters for request
    params_search_album = (
        ('q', request.form['autocomplete']),
        ('type', 'album'),
        ('limit', '1'),
        ('offset', '0'),
    )

    # Search albums and get ID, name and artists
    result_search_album = requests.get(
        'https://api.spotify.com/v1/search', headers=session.get('headers'), params=params_search_album)
    album_counter = 0
    album_id_list = []
    album_name_list = []
    album_artist_list = []
    album_picture_url_list = []

    # Count items in album search
    json_result_search_album = result_search_album.json()
    album_amount = len(json_result_search_album['albums']['items'])

    # Fill album_id, album_name and album_artist list
    while(album_counter < album_amount):
        album_id = json_result_search_album['albums']['items'][album_counter]['id']
        album_id_list.append(album_id)
        album_name = json_result_search_album['albums']['items'][album_counter]['name']
        album_name_list.append(album_name)
        album_artist = json_result_search_album['albums']['items'][album_counter]['artists'][0]['name']
        album_artist_list.append(album_artist)
        album_picture_url = json_result_search_album['albums']['items'][album_counter]['images'][1]['url']
        album_picture_url_list.append(album_picture_url)
        album_counter += 1

    # Store data in session
    session['album_id_list'] = album_id_list
    session['album_name_list'] = album_name_list
    session['album_artist_list'] = album_artist_list
    session['album_picture_url_list'] = album_picture_url_list
    session['album_amount'] = album_amount
    return redirect('add_songs')


@app.route('/add_songs', methods=['GET', 'POST'])
# add_songs function
# takes data from the search_album function and stores it
# returns it to add_songs.html
# renders add_songs.html
def add_songs():
    # Get the variables from session
    album_name_list = session.get('album_name_list')
    album_artist_list = session.get('album_artist_list')
    album_picture_url_list = session.get('album_picture_url_list')
    album_amount = session.get('album_amount')
    return render_template("add_songs.html",
                           album_name_list=album_name_list,
                           album_artist_list=album_artist_list,
                           album_picture_url_list=album_picture_url_list,
                           item_amount=album_amount)


@app.route('/fill_playlist', methods=['GET', 'POST'])
# fill_playlist function
# finds the amount of tracks in an album and creates a while loop to add all songs to a playlist
# redirects to search_album function
def fill_playlist():
    # Get album ID album
    album_id_list = session.get('album_id_list')

    # Get track IDs and amount of tracks from Album, depending on which Album is chosen
    value_form = request.form['fill_playlist']

    # Get the right album_id from the album_id_list
    album_id = album_id_list[int(value_form)]

    # Send request to the web API
    result_get_album = requests.get(
        f'https://api.spotify.com/v1/albums/{album_id}', headers=session.get('headers'))
    json_result_get_album = result_get_album.json()

    # Get the amount of tracks in the album
    total_tracks = json_result_get_album['total_tracks']

    # Adding all songs to the earlier created playlist
    song_counter = 0
    while(song_counter < total_tracks):
        session['song_id'] = json_result_get_album['tracks']['items'][song_counter]['id']
        add_song_to_playlist()
        song_counter += 1

    return redirect('search_album')


@app.route('/merge_playlists_index', methods=['GET', 'POST'])
# merge_playlists_index function
# calls function to get all playlists and stores the data
# returns the values to the merge_playlists_index.html
# renders merge_playlists_index.html
def merge_playlists_index():
    get_all_playlists()
    playlist_amount_user = session.get("playlist_amount_user")
    playlist_name_list = session.get("playlist_name_list")
    playlist_id_list = session.get("playlist_id_list")

    # Get the argument "playlist_error"
    playlist_error = request.args.get('playlist_error')

    return render_template("merge_playlists_index.html",
                           playlist_id_list=playlist_id_list,
                           playlist_name_list=playlist_name_list,
                           playlist_amount=playlist_amount_user,
                           playlist_error=playlist_error)


@app.route('/merge_playlists', methods=['GET', 'POST'])
# merge_playlists function
# gets various data to then make a while loop, to fill a playlist with all songs from all playlists
# redirects to merge_playlists_index function
def merge_playlists():
    # Define parameters for request
    params_list_playlist = (
        ('fields', 'items(track(id))'),
        ('limit', '100'),
        ('offset', '0'),
    )

    # Define data for request
    a = '{'
    name = request.form['new_playlist_name']
    false = 'false'
    b = '}'

    # Get playlist IDs
    merge_playlist_values = request.form.getlist('merge_playlist_value')

    # Count playlists checked
    playlist_count = len(merge_playlist_values)

    # If no name is entered into the "Playlist Name" form, set the argument "playlist_error" = 1
    if name == "":
        return redirect(url_for('merge_playlists_index', playlist_error='1'))

    # If a name is entered, create the playlist with the given name
    else:
        session['data_create_playlist'] = f'{a}"name":"{name}","description":"Platzhalter Beschreibung","public":{false}{b}'

        # call function to create playlist
        create_new_playlist()

        # Loop to add songs from checked playlists to new playlist
        i = 0
        while(i < playlist_count):
            result_get_playlist_tracks = requests.get(
                f'https://api.spotify.com/v1/playlists/{merge_playlist_values[i]}/tracks', headers=session.get('headers'), params=params_list_playlist)
            json_result_get_playlist_tracks = result_get_playlist_tracks.json()
            song_count = len(json_result_get_playlist_tracks['items'])
            song_counter = 0
            while(song_counter < song_count):
                session['song_id'] = json_result_get_playlist_tracks['items'][song_counter]['track']['id']
                add_song_to_playlist()
                song_counter += 1
            i += 1

    return redirect('/merge_playlists_index')


# get_all_playlists function
# makes a request to the web API, to get all playlists from user
def get_all_playlists():
    # Define parameters for request
    params = (
        ('limit', '50'),
        ('offset', '0'),
    )

    # Get all playlists in users library
    user_id = session.get('user_id')
    result_user_playlists = requests.get(
        f'https://api.spotify.com/v1/users/{user_id}/playlists', headers=session.get('headers'), params=params)
    json_result_user_playlists = result_user_playlists.json()

    # Count items
    playlist_amount_total = len(json_result_user_playlists['items'])

    # Only count playlists which are owned by user or collaborative
    playlist_counter = 0
    playlist_id_list = []
    playlist_name_list = []
    while(playlist_counter < playlist_amount_total):
        if(json_result_user_playlists['items'][playlist_counter]['owner']['display_name'] == session.get('user_id')):
            playlist_id = json_result_user_playlists['items'][playlist_counter]['id']
            playlist_id_list.append(playlist_id)
            playlist_name = json_result_user_playlists['items'][playlist_counter]['name']
            playlist_name_list.append(playlist_name)
        playlist_counter += 1

    # Get amount of playlists of user
    playlist_amount_user = len(playlist_id_list)
    session["playlist_id_list"] = playlist_id_list
    session["playlist_name_list"] = playlist_name_list
    session["playlist_amount_user"] = playlist_amount_user

    return None


# create_new_playlist function
# makes a request to the web API, to create a playlist with a given name
def create_new_playlist():
    # Get data
    data_create_playlist = session.get('data_create_playlist')

    # Send request to create playlist
    user_id = session.get('user_id')
    response_create_playlist = requests.post(
        f'https://api.spotify.com/v1/users/{user_id}/playlists', headers=session.get('headers'), data=data_create_playlist)
    json_response_create_playlist = response_create_playlist.json()
    session['playlist_id'] = json_response_create_playlist['id']

    return None


# add_songs_to_playlist function
# makes a request to the web API, to fill the playlist with songs
def add_song_to_playlist():
    song_id = str(session.get('song_id'))
    params_fill_playlist = (
        ('position', 0),
        ('uris', f'spotify:track:{song_id}'),
    )
    playlist_id = session.get('playlist_id')
    requests.post(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
                  headers=session.get('headers'), params=params_fill_playlist)

    return None


if __name__ == "__main__":
    app.run(debug=True)
