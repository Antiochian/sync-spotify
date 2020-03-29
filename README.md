# sync-spotify
Synchronise multiple Spotify accounts together (for group videochats)

Inprogress build!
Will clean the code and this README up when its more feature-complete

To Do:
 - [x] ~set up API authorisation token system for N users~
 - [x] ~detect new track event (change current track, pause, seek forward/back)~
 - [x] ~apply new track event globally to all users~
 - [x] ~account for latency delay in API calls~
 - [ ] account for latency delay in client response
 - [ ] Fix edge cases (device change, connection loss, drop-in/drop-out, advert play, etc)
 - [ ] Make CLI
 - [ ] Make GUI (?)

Bugs to fix:
 - [ ] Doesn't work with podcasts
 - [ ] Doesn't pause correctly ~10% of the time
 - [ ] Messy transition between tracks in queue
