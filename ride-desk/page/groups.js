  var GROUPS = [
    { id: "announce", title: "Spoken turn directions", intro: "When the phone speaks before each turn.", items: [
      { k: "firstWarningMetres", label: "Early warning before a turn", help: "How far before a turn the rider first hears about it.", min: 60, max: 400, step: 10, rec: 160, unit: "m",
        hear: function (v) { return "“In " + sayDist(v) + ", turn left onto Venture Drive.” About " + secs(v) + " before the turn."; } },
      { k: "turnMetres", label: "Turn now", help: "How far before the turn the phone says the turn itself.", min: 10, max: 80, step: 5, rec: 35, unit: "m",
        hear: function (v) { return "“Turn left onto Venture Drive.” About " + secs(v) + " before the turn."; } },
      { k: "mergeNextCueWithinMetres", label: "Turns close together", help: "If the next turn is this close, it is said straight after the current one. Set to 0 to never join them.", min: 0, max: 250, step: 10, rec: 90, unit: "m",
        hear: function (v) { return v === 0 ? "Each turn is said on its own." : "“Turn left onto Venture Drive. Then turn right onto Gateway Drive.” when the second turn is within " + v + " m."; } },
      { k: "skipFirstWarningIfCuesCloserThanMetres", label: "Skip the early warning between quick turns", help: "When two turns are closer than this, the second one gets no early warning, so the rider is not talked over.", min: 0, max: 300, step: 10, rec: 110, unit: "m",
        hear: function (v) { return v === 0 ? "Every turn gets an early warning." : "Turns less than " + v + " m apart: only the “turn now” line."; } },
      { k: "cautionWarningMetres", label: "Early warning for caution cues", help: "For cues marked Danger in Ride with GPS, such as a busy road crossing.", min: 60, max: 400, step: 10, rec: 120, unit: "m",
        hear: function (v) { return "“Caution. In " + sayDist(v) + ", cross Cooroy Noosa Road with care.”"; } }
    ]},
    { id: "offRoute", title: "Going off route", intro: "When riders leave the line on the map.", items: [
      { k: "metres", label: "Counts as off route", help: "How far from the line before the rider is treated as off route. Lower is stricter; GPS can wander 10 to 20 m near trees and buildings.", min: 25, max: 150, step: 5, rec: 50, unit: "m",
        hear: function (v) { return "Further than " + v + " m from the line counts as off route."; } },
      { k: "readings", label: "Wait before warning", help: "How many location readings in a row must be off route before the warning. Phones take about one a second.", min: 1, max: 10, step: 1, rec: 3, unit: "",
        hear: function (v) { return "“You’re off the route. The route line is 80 metres away.” after about " + v + (v === 1 ? " second." : " seconds."); } },
      { k: "repeatSeconds", label: "Repeat the warning every", help: "While the rider stays off route.", min: 20, max: 600, step: 10, rec: 60, unit: "s",
        hear: function (v) { return "Repeats every " + dur(v) + " until they are back on the line."; } }
    ]},
    { id: "stops", title: "Stops", intro: "Points of interest and caution notes set in Ride with GPS.", items: [
      { k: "triggerMetres", label: "Open a stop when the rider is within", help: "On rides with point of interest stories on, the stop card pops up and its short overview is read out.", min: 20, max: 200, step: 5, rec: 60, unit: "m",
        hear: function (v) { return "“You have reached a point of interest. Laguna Lookout.” within " + v + " m."; } },
      { k: "cautionWarningMetres", label: "Warn about caution stops this far ahead", help: "Such as “Path can be slippery when wet”.", min: 30, max: 300, step: 10, rec: 90, unit: "m",
        hear: function (v) { return "“Caution. Path can be slippery when wet.” about " + secs(v) + " before it."; } }
    ]},
    { id: "screen", title: "Screen", intro: "What riders start with. They can change these in the app. The screen always stays on during a ride (a locked phone cannot speak directions), so there is no setting for that.", items: [
      { k: "batterySaver", label: "Battery saver", help: "Blacks out the screen between turns and lights it up for each turn, stop or warning. A black screen uses very little power on most phones.", toggle: true, rec: false },
      { k: "readStoriesAloud", label: "Point of interest stories for a new ride", help: "Only used for a ride that has no setting of its own yet. Each ride's own switch is on its card under Rides.", toggle: true, rec: true },
      { k: "wakeBeforeTurnMetres", label: "Battery saver lights up before a turn", help: "Only used when battery saver is on.", min: 80, max: 1000, step: 10, rec: 250, unit: "m",
        hear: function (v) { return "The screen lights up about " + secs(v) + " before each turn."; } },
      { k: "blackoutAfterSeconds", label: "Battery saver blacks out after", help: "Seconds without a tap before the screen goes black again.", min: 5, max: 120, step: 5, rec: 20, unit: "s",
        hear: function (v) { return "Goes black " + dur(v) + " after the last tap."; } }
    ]},
    { id: "speeds", title: "Riding time estimates", intro: "Average riding speed for each kind of ride, used for “Riding time” on the ride page and “About 40 min at an easy pace” while riding. It is time on the bike only, not stops.", items: [
      { k: "scenic", label: "Scenic e-bike rides", help: "Full Noosa, Kids & Family, Surf Beaches, Mt Tinbeerwah, Mt Tinbeerwah One Way, North Shore.", min: 3, max: 40, step: 0.5, rec: 15, unit: "km/h",
        hear: function (v) { return "Full Noosa (34.1 km) shows as " + rideTime(34.1, v) + "."; } },
      { k: "mtb", label: "Mountain bike rides from the shop", help: "Wooroi & Wetlands, Tewantin MTB Trails, Lake Weyba and Tewantin Forest Loop.", min: 3, max: 40, step: 0.5, rec: 12, unit: "km/h",
        hear: function (v) { return "Wooroi & Wetlands (24.7 km) shows as " + rideTime(24.7, v) + "."; } },
      { k: "gravel", label: "Gravel rides from the shop", help: "Ringtail Loop, Yurol Forest Loop.", min: 3, max: 40, step: 0.5, rec: 18, unit: "km/h",
        hear: function (v) { return "Yurol Forest Loop (50.4 km) shows as " + rideTime(50.4, v) + "."; } },
      { k: "road", label: "Road rides from the shop", help: "Noosa Tri Sampler, Coolum Coast, Lakes Ride with Garmin Hill, Pomona Loop.", min: 3, max: 40, step: 0.5, rec: 25, unit: "km/h",
        hear: function (v) { return "Coolum Coast Ride (71.1 km) shows as " + rideTime(71.1, v) + "."; } },
      { k: "hinterlandMtb", label: "Hinterland mountain bike rides", help: "Peak to Peak, Country Towns & Canopies, Everglades Vistas, Forest, Farms & Noosa, Rockpools & Ridgelines (MTB).", min: 3, max: 40, step: 0.5, rec: 15, unit: "km/h",
        hear: function (v) { return "Rockpools & Ridgelines MTB (80.4 km) shows as " + rideTime(80.4, v) + "."; } },
      { k: "hinterlandGravel", label: "Hinterland gravel rides", help: "Pomona to Noosa through to Through Lake Country, the nine point to point gravel rides.", min: 3, max: 40, step: 0.5, rec: 20, unit: "km/h",
        hear: function (v) { return "Through Lake Country (115.7 km) shows as " + rideTime(115.7, v) + "."; } },
      { k: "walk", label: "Walking", help: "", min: 1, max: 10, step: 0.5, rec: 4.5, unit: "km/h", hear: function (v) { return "5 km shows as " + rideTime(5, v) + "."; } },
      { k: "kayak", label: "Kayak", help: "For paddle routes when they are added.", min: 1, max: 15, step: 0.5, rec: 5, unit: "km/h", hear: function (v) { return "8 km shows as " + rideTime(8, v) + "."; } }
    ]}
  ];
