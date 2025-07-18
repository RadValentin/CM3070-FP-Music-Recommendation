# CM3070-FP-Music-Recommendation

## Installation

```bash
pip install Django numpy pandas scikit-learn djangorestframework
```

```bash
# populate DB
cd backend/
python scripts/populate_db.py
```

## Folder Structure

- `backend`
  - `music_recommendation` - the main Django project
  - `recommend_api` - the Django app that provides the music recommendation API and serves the HTML/JS/CSS assets
- `frontend` - assets that are bundled into static assets and served by the `recommend_api` app

## Prototype App

As a placeholder for the final dataset, I used the ["Spotify Million Song Dataset"](https://www.kaggle.com/datasets/notshrirang/spotify-million-song-dataset) licensed under [CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/) from Kaggle.

Prototype user flow:
- User finds the song he likes using the front-end
  - Back-end should support searching for songs by title, returning matches with their IDs
- Dataset is loaded, a machine learning model is trained on it

For 57650 songs it takes 2,85 GB of disk space to store their associated TF-IDF vectors. This is a noticeable increase in storage requirements as the lyrics themselves only take up 71 MB.

Some insights on the vectors themselves:
- Each has a 10k features upper bound
- They're sparsely populated, most values being zero
- They're stored in the DB as raw JSON which will involve some overhead when accessing and processing them
- Saving the data to the DB takes around 10 minutes

Similar songs can be identified by calculating the cosine similarity between the original song's and all other songs TF-IDF vectors. The songs with the highest values (between -1 and 1) will also be closest in terms of their lyrical content.

In order to increase performance I decided to store the vectors as a separate file instead and only keep the song metadata in the DB.

### Notes for project

I've chosen "NextTrack: A music recommendation API" as the template for my project. The main reason is that I find the domain area interesting and it addresses an real shortcoming of current-day music platforms which I often come across. It always happens that I get stuck in a loop of either the same songs or songs I don't enjoy. I think it would be interesting to solve this issue. Plus, I can use the project to demonstrate my web development skills when applying for jobs later on.

## 7.2 Project Idea 2: NextTrack: A music recommendation API

**What problem is this project solving, or what is the project idea?**  
Design a music recommendation API that gives a ‘next track’ based on an HTTP request, providing listening history and some preference parameters, along with data about the tracks available.

**What is the background and context to the question or project idea above?**  
Music recommendation and playlist generation systems are popular and much researched.  
It’s quite common for these to operate within applications that users log into, and which profile that user based on their listening habits. This has implications for privacy. It can also be undermined by shared accounts and listening (for example, a household with a child, may wind up with nursery rhymes in the recommendations).  
You will build a RESTful recommendation system with no user tracking. Instead, the user will provide a sequence of track identifiers that the next track should follow from, and some preference parameters (which you can choose).  
The system will use data from external sources, such as MusicBrainz, Genius.com, Spotify, Wikidata to inform its choices.  

**Here are some recommended sources for you to begin your research.**

The ISMIR conference (ismir.net) has many papers on recommender systems that should give an idea of the sorts of things you could do. There’s no necessity to use audio features – some of Brian Whitman’s work in early ISMIR conferences uses non-content information, such as metadata and online reviews.

**What would the final product or final outcome look like?**  
A RESTful API that takes a set of track identifiers and other parameters and returns the ID of a suitable next track.  
There should be some form of evaluation (for example, based on user testing or some prior work giving good sequences).

**What would a prototype look like?**  
The basic API. This could return tracks at random for prototyping purposes, but it should reproduce the input/output format.  
If a frontend is to be implemented, a basic implementation with music player (e.g. via YouTube or logged-in Spotify).

**What kinds of techniques/processes/CS fundamentals are relevant to this project?**  
Web API, UI/UX, Music Information Retrieval

**What would the output of these techniques/processes/CS fundamentals look like?**  
A stateless playlist generating API that has a strategy for choosing new tracks that is better than random selection.

**How will this project be evaluated and assessed by the student (i.e. during iteration of the project)? What criteria are important?**
- A good overview of playlists/recommender systems and what users might want
- A well-thought-through RESTful API that offers some user control
- Sensible evaluation of the results

**For this brief, what might a minimum pass (e.g. 3rd) student project look like?**  
A working API that gets some data from elsewhere, and combines it with user-provided information to choose a track.

**For this brief, what might a good (e.g. 2:2 – 2:1) student project look like?**  
A literature review that identifies a good strategy for recommending the next track, a working API that offers real choice to the user.  
A Web application that demonstrates that the API works. Good evaluation (such as user testing)

**For this brief, what might an outstanding (e.g. 1st) student project look like?**  
An insightful overview of recommendation approaches and the data that is available to a server process.  
An API that recommends based on well-chosen parameters.  
A web application that provides an interactive music playing experience.  
Strong user testing and reflection on the results of it (ideally, modifications based on user testing, which are themselves tested).