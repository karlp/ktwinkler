# twinkler multi
Instead of trying to make the tiniest little thing stuffed into a battery case, when we already know that they have buttons on different sides and locations, so it would never be one size fits all anyway, let's make something a bit different.

Just make it as a controller board, with a couple of channels, so you can just plug in some strings chopped off cheap kits.  Also. let's play with two cpus, and some different motor controllers to see what's "best"

Try allll the things!


# To try
* different cheap motor chips
* smt screw mount shits.
* battery ... wots?


# Errors/lessons from first production run
lol, the H5VU25UC uni tvs I chose, I totally misread the internal schematic, and connected it with 3/8 being vcc/gnd, ala bidir.  Soooo, that has a nice built in short :)  Easy fix, remove the tvs on these boards, but need to fix the part in my lib!
