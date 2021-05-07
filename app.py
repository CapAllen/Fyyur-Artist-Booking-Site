#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import (Flask, render_template, request,
                   Response, flash, redirect, url_for)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *

import datetime
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, or_
from flask_migrate import Migrate
from models import db, Venue, Artist, Show
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
csrf = CSRFProtect()
csrf.init_app(app)

migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    venues = Venue.query.all()

    places = Venue.query.distinct(Venue.city, Venue.state).all()

    for place in places:
        data.append({
            'city': place.city,
            'state': place.state,
            'venues': [{
                'id': venue.id,
                'name': venue.name,
                'num_upcoming_shows': len([show for show in venue.shows if
                                          show.start_time > datetime.now()])
            } for venue in venues if
                venue.city == place.city and venue.state == place.state]
        })
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    term = request.form.get('search_term', '').lower()

    data = Venue.query.filter(
        or_(
            func.lower(Venue.city).like(f'%{term}%'),
            func.lower(Venue.state).like(f'%{term}%'),
            func.lower(Venue.name).like(f'%{term}%')
        )
    )

    return render_template('pages/search_venues.html', results={"count": data.count(),
                                                                "data": data}, search_term=request.form.get('search_term', ''), form=VenueForm())


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    venue_data = []

    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    shows = db.session.query(Show, Artist, Venue).join(Artist).join(Venue). \
        filter(
        Show.venue_id == venue_id,
        Show.artist_id == Artist.id
    ). \
        all()

    past_shows = []
    upcoming_shows = []

    for show in shows:
        temp_show = {
            'artist_id': show.Artist.id,
            'artist_name': show.Artist.name,
            'artist_image_link': show.Artist.image_link,
            'start_time': show.Show.start_time.strftime("%m/%d/%Y, %H:%M")
        }
        if show.Show.start_time <= datetime.now():
            past_shows.append(temp_show)
        else:
            upcoming_shows.append(temp_show)

    # object class to dict
    data = vars(venue)

    data['past_shows'] = past_shows
    data['upcoming_shows'] = upcoming_shows
    data['past_shows_count'] = len(past_shows)
    data['upcoming_shows_count'] = len(upcoming_shows)

    venue_data = {
        'id': venue.id,
        'name': venue.name,
        'genres': venue.genres,
        'address': venue.address,
        'city': venue.city,
        'state': venue.state,
        'phone': venue.phone,
        'website_link': venue.website_link,
        'facebook_link': venue.facebook_link,
        'seeking_talent': venue.seeking_talent,
        'seeking_description': venue.seeking_description,
        'image_link': venue.image_link
    }

    venue_data.update(data)
    return render_template('pages/show_venue.html',
                           venue=venue_data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False

    form = VenueForm()

    if form.validate_on_submit():
        try:
            venue = Venue(
                name=request.form.get('name'),
                city=request.form.get('city'),
                state=request.form.get('state'),
                address=request.form.get('address'),
                phone=request.form.get('phone'),
                website_link=request.form.get('website_link'),
                image_link=request.form.get('image_link'),
                genres=', '.join(request.form.getlist('genres')),
                facebook_link=request.form.get('facebook_link'),
                seeking_talent=request.form.get('seeking_talent') == 'y',
                seeking_description=request.form.get('seeking_description')
            )

            db.session.add(venue)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            error = True
            print(logging.error("Fatal error: " + str(e)))
        finally:
            db.session.close()

        if error:
            flash('An error occurred. Venue ' +
                  request.form['name'] + ' could not be listed.')
        else:
            flash('Venue ' + request.form['name'] +
                  ' was successfully listed!')

        return render_template('pages/home.html')

    else:
        return render_template('forms/new_venue.html', form=form)


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    success = True
    error = ''
    venue = Venue.query.get(venue_id)

    try:
        db.session.delete(venue)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        success = False
        print(logging.error("Fatal error: " + str(e)))
    finally:
        db.session.close()

    if success:
        flash('Venue ' + venue.name + ' was successfully deleted!')
    else:
        error = 'An error occurred. Venue ' + venue.name + ' could not be deleted.'
        flash(error)
    return jsonify({'success': success, 'error': error})

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    artists_data = []

    artists = Artist.query.all()

    for artist in artists:
        artists_data.append({
            "id": artist.id,
            "name": artist.name
        })

    return render_template('pages/artists.html',
                           artists=artists_data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')

    artists = Artist.query.filter(
        Artist.name.like('%' + search_term + '%')).all()

    artist_data = []

    for artist in artists:
        artist_data.append({
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": len([show for show in artist.shows if
                                       show.start_time > datetime.now()])
        })

    search = {
        "count": len(artists),
        "data": artist_data
    }

    return render_template('pages/search_artists.html',
                           results=search, search_term=request.form.get
                           ('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist_data = []

    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    shows = db.session.query(Show, Venue).join(Venue). \
        filter(
        Show.artist_id == artist_id,
        Show.venue_id == Venue.id
    ). \
        all()

    past_shows = []
    upcoming_shows = []

    for show in shows:
        temp_show = {
            'venue_id': show.Venue.id,
            'venue_name': show.Venue.name,
            'venue_image_link': show.Venue.image_link,
            'start_time': show.Show.start_time.strftime("%m/%d/%Y, %H:%M")
        }
        if show.Show.start_time <= datetime.now():
            past_shows.append(temp_show)
        else:
            upcoming_shows.append(temp_show)

    # object class to dict
    data = vars(artist)

    data['past_shows'] = past_shows
    data['upcoming_shows'] = upcoming_shows
    data['past_shows_count'] = len(past_shows)
    data['upcoming_shows_count'] = len(upcoming_shows)

    artist_data = {
        'id': artist.id,
        'name': artist.name,
        'genres': artist.genres,
        'city': artist.city,
        'state': artist.state,
        'phone': artist.phone,
        'website_link': artist.website_link,
        'facebook_link': artist.facebook_link,
        'seeking_venue': artist.seeking_venue,
        'seeking_description': artist.seeking_description,
        'image_link': artist.image_link
    }

    artist_data.update(data)
    return render_template('pages/show_artist.html',
                           artist=artist_data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first_or_404()

    form = ArtistForm(obj=artist)

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    artist = Artist.query.get(artist_id)
    form = ArtistForm()
    error = False

    if form.validate_on_submit():
        try:
            artist.name = request.form.get('name')
            artist.city = request.form.get('city')
            artist.state = request.form.get('state')
            artist.phone = request.form.get('phone')
            artist.website_link = request.form.get('website_link')
            artist.image_link = request.form.get('image_link')
            artist.genres = ', '.join(request.form.getlist('genres'))
            artist.facebook_link = request.form.get('facebook_link')
            artist.seeking_venue = request.form.get('seeking_venue') == 'y'
            artist.seeking_description = request.form.get(
                'seeking_description')

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            error = True
            print(logging.error("Fatal error: " + str(e)))
        finally:
            db.session.close()

        if error:
            flash('An error occurred. Artist ' +
                  request.form.get('name') + ' could not be updated.')
        else:
            flash('Artist ' + request.form.get('name') +
                  ' was successfully updated!')

        return redirect(url_for('show_artist', artist_id=artist_id))

    else:
        return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.filter_by(id=venue_id).first_or_404()

    form = VenueForm(obj=venue)

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    form = VenueForm(request.form, meta={'csrf': True})
    form.populate_obj(venue)
    if form.validate():
        try:
            db.session.commit()

            flash('Venue ' + form.name.data + ' was successfully updated!')
        except venue:
            flash('An error occurred. Venue ' +
                  form.name.data + ' could not be ppdated.')
            db.session.rollback()
            print(sys.exc_info())
        finally:
            db.session.close()
    else:
        message = []
        for field, err in form.errors.items():
            message.append(field + ' ' + '|'.join(err))
        flash('Errors ' + str(message))

    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False
    form = ArtistForm()

    if form.validate_on_submit():
        try:
            artist = Artist(
                name=request.form.get('name'),
                city=request.form.get('city'),
                state=request.form.get('state'),
                phone=request.form.get('phone'),
                website_link=request.form.get('website_link'),
                image_link=request.form.get('image_link'),
                genres=', '.join(request.form.getlist('genres')),
                facebook_link=request.form.get('facebook_link'),
                seeking_venue=request.form.get('seeking_venue') == 'y',
                seeking_description=request.form.get('seeking_description')
            )

            db.session.add(artist)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            error = True
            print(logging.error("Fatal error: " + str(e)))
        finally:
            db.session.close()

        if error:
            flash('An error occurred. Artist ' +
                  request.form['name'] + ' could not be listed.')
        else:
            flash('Artist ' + request.form['name'] +
                  ' was successfully listed!')

        return render_template('pages/home.html')
    else:
        return render_template('forms/new_artist.html', form=form)


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    shows_data = []
    shows = Show.query.all()

    for show in shows:
        shows_data.append({
            "venue_id": show.venue_id,
            "venue_name": Venue.query.filter_by
            (id=show.venue_id).first().name,
            "artist_id": show.artist_id,
            "artist_name": Artist.query.filter_by
            (id=show.artist_id).first().name,
            "artist_image_link": Artist.query.filter_by
            (id=show.artist_id).first().image_link,
            "start_time": str(show.start_time)
        })

    return render_template('pages/shows.html', shows=shows_data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm()
    if form.validate_on_submit():
        try:
            artist_id = request.form['artist_id']
            venue_id = request.form['venue_id']
            start_time = request.form['start_time']

            show = Show(artist_id=artist_id, venue_id=venue_id,
                        start_time=start_time)

            db.session.add(show)
            db.session.commit()

            flash('Show was successfully listed!')
        except show:
            db.session.rollback()
            flash('An error occurred. Show could not be listed.')
        finally:
            db.session.close()
    else:
        flash('Posting a show failed due to validation error(s)!')
        flash(form.errors)
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
