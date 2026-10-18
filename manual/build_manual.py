"""The words of the three Ride Guide manuals in EO Crew, as EO Crew document sections (DocSection blocks).

EO-HI-10    Ride Guide: the app and our rides          all staff       (Part 1: setting customers up)
EO-HI-10.1  Ride Guide: managing rides on the Ride Desk  managers only   (Part 2)
EO-HI-10.2  Ride Guide: technical appendix               managers only   (Part 3)

EO Crew is the master for these words once they are in it (managers can edit them in Write view). This file is the
version Claude wrote, kept so a later rewrite starts from it; manual/written.json says which document and section each
fact in the code feeds, so the weekly drift check knows what to rewrite when the app changes.
Pictures: {"type": "ride_screens", "group": "<group>"} shows the screenshots the build retakes every night
(scripts/staff_screens.py). Run: python3 manual/build_manual.py > manual/sections.json
"""
import json

SITE = 'elementoutdoors.github.io/routes'
DESK = 'https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18'
BEN_DESK = 'https://claude.ai/artifact/YGE5oznqmZ26StQaAuKRTd'
REPO = 'https://github.com/elementoutdoors/routes'
LIB = 'https://elementoutdoors.github.io/routes/library.html'
REVIEW = 'https://claude.ai/artifact/XSdaNvQMw8tYpaqSiBz7Tp'
BOOKLET = '/hire?tab=rides'


def H(t): return {'type': 'heading', 'text': t}
def T(t): return {'type': 'text', 'text': t}
def L(*items): return {'type': 'list', 'items': list(items)}
def S(*steps): return {'type': 'step', 'steps': list(steps)}
def NOTE(t): return {'type': 'callout', 'tone': 'note', 'text': t}
def WARN(t): return {'type': 'callout', 'tone': 'warn', 'text': t}
def MUST(t): return {'type': 'callout', 'tone': 'must', 'text': t}
def TAB(header, rows): return {'type': 'table', 'header': header, 'rows': rows}
def SAY(t): return {'type': 'script', 'text': t}
def SHOTS(g): return {'type': 'ride_screens', 'group': g}


def part1(D10_1, D10_2):
    return [
        ('What the Ride Guide is', [
            T("The Ride Guide is our self guided ride map on the customer's own phone. It replaced the Ride with GPS app in October 2026. It shows the ride on a map with spoken and written directions, stops at the places along the way with their stories, partner offers, and a finish card that asks how the ride went."),
            L("There's no app to download and no account or password. It opens in the phone's normal web browser (Safari on an iPhone, Chrome on Android).",
              "Each ride has its own private link, QR code and 6 character route code. The Ride Guide home page on its own won't open a ride.",
              "Once a ride is opened with signal it is saved to the phone with its map, voice and stops, so it keeps working with no signal.",
              "Directions are spoken out loud and shown on screen, in nine languages: English, German, French, Spanish, Italian, Dutch, Chinese, Japanese and Korean.",
              "Every ride is either a Bike On or a By Earth and Ocean ride, and shows that brand's logo and colours.",
              "Bike On and By Earth and Ocean rides both use it, from the scenic e-Bike rides from the shop to the hinterland point to point rides."),
            H('The three parts of this manual'),
            TAB(['Part', 'For', 'What is in it'], [
                ['EO-HI-10 (this one)', 'All staff', 'What the Ride Guide is, setting a customer up, every screen and setting, what to tell customers, our rides and fixing common problems.'],
                ['EO-HI-10.1', 'Managers', f'Changing rides, stories, photos, offers and the rider settings on the Ride Desk, the booklet, and the limits of the Ride Guide. [[doc:{D10_1}]]'],
                ['EO-HI-10.2', 'Managers', f'The technical appendix: where every piece of information lives, how it gets to the phone, the accounts behind it, and how to fix or change things without Claude. [[doc:{D10_2}]]']]),
            NOTE('The pictures in these manuals are taken by the Ride Guide itself every night, so they always show the app as customers see it. The numbers on each picture match the list under it.'),
        ]),
        ('Setting a customer up', [
            H('How customers get their ride'),
            L('The link in their booking email: they tap it and the ride opens.',
              "In store: they scan the ride's QR code with their phone camera.",
              "They aren't given a card to keep. If they lose the ride, \"Getting back to this route\" on the ride page shows their route code, and typing it on the Ride Guide home page reopens it."),
            SHOTS('setup'),
            H('Every ride\'s QR code and route code'),
            T('Live from the Ride Guide: a new ride, or a ride whose code is changed, shows here by itself. Customers scan the code straight off this screen. Copy link gives the ride\'s link for an email or text.'),
            {'type': 'ride_qr'},
            WARN('QR codes, route codes and ride links are for staff and the customers on that ride. Never post them anywhere public (website, social media, listings): anyone with one can open the ride.'),
            H('Setting a customer up in store'),
            S('Check the booking for which ride they are doing, and that they booked the maps or our navigation phone. If they haven\'t chosen a ride, help them choose (see Our rides below).',
              "They scan that ride's QR code with the phone camera. It must open in their normal browser (Safari or Chrome), not a private tab or another app's browser. Check the ride name under the map is the right one.",
              'Set the language with the EN button, and km or miles with the km button, if they want.',
              'Wait for "Saved to your phone. Works with no signal." before they leave. This matters most on hinterland rides, where signal at the start is poor, so open the ride at the shop before the shuttle.',
              'Show them "Getting back to this route" so they know where their route code is.',
              'Ask if they want the stories at each place (Point of interest stories in Settings) and whether they want Battery saver.',
              'Tap Start riding at the shop, allow location when the phone asks, and turn the volume up.',
              'Tell them to keep the Ride Guide on screen the whole ride and never lock the phone (see What to tell every customer).',
              'Phone in the mount. Tell them to stop somewhere safe before touching it.'),
            H('Sending a ride by email or text'),
            L('Send the ride\'s link as a button ("Open your ride map") and the route code as a backup. Copy the link from the QR codes above.',
              'A QR code only helps someone reading on a computer.',
              f'On the phone: tell them to go to {SITE} and type the route code into "Have a route code?".'),
            H('Phone mounts'),
            L('Sealed paths and the North Shore: a universal phone holder is fine.',
              'Off road (MTB rides, and rough gravel): a Quad Lock is needed. A Quad Lock mount is $5 per booking for riders with their own Quad Lock case. We never hire cases.',
              'No Quad Lock case, or worried about battery: hire our navigation phone with a Quad Lock mount ($40 a day).'),
            H('Rules'),
            L('Route codes use capital letters and the numbers 3, 4, 6, 7 and 9 only. There is no O, I, L, zero or one in any code, so nothing can be mixed up.',
              'Never set a customer up on "Ben\'s test route". It is a short test loop, not a ride.',
              "If a ride's link is ever changed, its old QR code and route code stop working. This manual updates itself; reprint that ride's page of the booklet.",
              'Partner offers: the Land and Sea Brewery offer needs the physical voucher card, one per rider aged 18 or over, given when they get back. For the Fliteschool Noosa 10% offer they call 0477 418 419 and mention Bike On.'),
            NOTE('The Ride Guide is there to help, but finding their way is the rider\'s responsibility, and so is judging the risks along the ride. If they need picking up, recovery is charged (see When something goes wrong).'),
        ]),
        ('The app, screen by screen', [
            T('Every screen a rider sees, in the order they meet them. The numbers on each picture are listed underneath it.'),
            H('Riding'),
            T('Once they tap Start riding, the riding screen does everything. Directions are said before each turn ("In 150 metres, turn left onto ...") and again at the turn, with a short ding. A turn close behind another is added on ("Then turn right ...").'),
            SHOTS('riding'),
            L('Before they reach the route, the Ride Guide says how far away the start is and points them to the green marker. Directions start once they are on the line. This is normal on hinterland rides until the shuttle drops them off.',
              'Off route: after a few seconds more than about 50 metres from the line, it says "You\'re off the route" and shows how far away the line is. It doesn\'t give directions back: riders use the map. It says "Back on route" when they rejoin.',
              'Riding the wrong way: after about 150 metres backwards along the route it says "You may be riding the route backwards. Check the arrows on the line."',
              'Pause: for a coffee, a swim or a detour. While paused, directions, warnings, stops and offers are held and the screen can sleep. Resume carries on.',
              'Locked screen: if the phone was locked or they switched apps mid ride, the Ride Guide warns them when they come back that directions stopped while it was away.'),
            H('Stops and stories'),
            T('A stop pops up as the rider reaches a place on the ride (when stories are on), and its name and a short overview are read out. Caution stops (a busy crossing, a slippery path) always show a warning and are spoken ahead, even with stories off. Toilets, cafes and water are on the map and in the Stops list but never pop up.'),
            SHOTS('stops'),
            H('Offers and the finish'),
            T('Rider offers are listed under Offers. Land and Sea Brewery is over the road from the shop, so its offers come up near the end of the ride and on the finish card, never at the start. The finish card comes up once most of the ride (75%) has been ridden on that phone.'),
            SHOTS('finish'),
            NOTE('Riders who tap It was OK or Not great are offered an email or a call to us first, then the same review links. Google doesn\'t allow asking only happy customers for reviews.'),
        ]),
        ('Settings on the phone', [
            T('Riders open Settings from the ride page, or from the menu button on the riding screen. What they choose is kept on that phone. Most riders never need to change anything.'),
            SHOTS('settings'),
            TAB(['Setting', 'What it does', 'When to suggest it'], [
                ['Units', 'Kilometres or miles.', 'Visitors from the US or UK who think in miles.'],
                ['Language', 'Nine languages. Directions, stops, stories and the app\'s words all change.', 'Anyone more at home in German, French, Spanish, Italian, Dutch, Chinese, Japanese or Korean. If the phone has no voice for that language, directions show on screen and are spoken in English.'],
                ['Spoken directions', 'Turns the voice on or off. Directions still show on screen.', 'Almost never: the voice is the point.'],
                ['Natural voice', 'Our recorded voice, saved to the phone. Off uses the phone\'s own voice.', 'Only if the voice sounds wrong on their phone.'],
                ['Chime at turns', 'A short ding at each turn, even with the voice off.', 'Leave on.'],
                ['Point of interest stories', 'On: each place\'s card pops up and a short overview is read out. Off: places stay on the map and in the Stops list but aren\'t announced. Directions and safety warnings are always spoken.', 'On for sightseers. Off for riders who just want to ride. Each ride starts with our own choice (off on road and gravel rides and Tewantin MTB Trails).'],
                ['Battery saver', 'Blacks the screen out between turns (almost no power) and lights it up before each turn, at stops and when off route. Tap the screen to wake it.', 'Long rides, older phones, or a phone that wasn\'t fully charged.'],
                ['Map', 'Standard or satellite. Satellite needs signal.', 'Riders who like to see the ground.'],
                ['Download this ride as a GPX file', 'The route line for a Garmin, Wahoo or other bike computer. Only on road, gravel, MTB and hinterland rides.', 'Riders with a bike computer.']]),
            NOTE('The screen always stays on while riding, so there is no setting for that. The timings behind the voice and warnings are set for everyone on the Ride Desk (managers, EO-HI-10.1).'),
        ]),
        ('What to tell every customer', [
            T('The Ride Guide works best when riders know four things. Say them at the counter, in your own words.'),
            SAY('Keep the Ride Guide open on screen the whole ride and don\'t lock your phone. A locked phone can\'t give directions. If you want to save battery, turn on Battery saver in Settings: it blacks out the screen between turns and lights it up before each one.\n\nIf you stop for a coffee or a swim, tap Pause, then Resume when you\'re ready.\n\nIf you go off the route, use the map to get back to the line. It tells you when you\'re back on route.\n\nIf you close it by mistake, open the same web address again, or type your route code. It\'s under "Getting back to this route".'),
            L('Start with a full charge, and volume up. Bluetooth headphones or a car connection take the voice with them.',
              'Signal isn\'t needed once the ride says "Saved to your phone". Satellite view and "More about this place" need signal.',
              'Use the normal browser, not a private tab: a private tab forgets the ride when it closes.',
              'The riding time on screen is time on the bike only. Go by the time we booked, and bikes are back by 4pm.',
              'Stop somewhere safe before touching the phone.'),
        ]),
        ('Our rides', [
            T('Every ride in the Ride Guide, grouped by kind of ride. Each ride has its staff notes (what it is sold as, which bike, time to allow, who it suits and who it doesn\'t), then its description, distance, riding time, stops and cautions, live from the Ride Guide.'),
            {'type': 'ride_list'},
            NOTE('Every word about a ride, and its staff notes, is changed on its Ride Desk card (managers, EO-HI-10.1). The route, the turns and the stops are changed in Ride with GPS. Never type ride details anywhere else.'),
            H('Ride sheets and the booklet'),
            T(f'Every ride has an A4 ride sheet with its 3D map, photo, details and QR code. The sheets for both brands make up the rides booklet on the counter. [Open the ride sheets and the whole booklet]({BOOKLET}) (Hire desk, Rides tab, then Whole booklet). They rebuild themselves whenever the Ride Desk or Ride with GPS changes.'),
            H('Which bike for which kind of ride'),
            T('Rides come in a few kinds. Use the kind to choose the bike, then check the ride\'s own notes above for anything special.'),
            TAB(['Kind of ride', 'Bike', 'Know before they go'], [
                ['Bike On scenic e-Bike rides from the shop (sealed paths and quiet roads)', 'Comfort Deluxe or Standard Cruiser e-Bike recommended. Fat tyre e-Bikes, hybrids and Standard Hardtail also suit. Family rides also suit kids bikes and kids carriers.', 'e-Bike law applies: 16 and over with a drivers licence; 12 to 17 only with a parent, grandparent or legal guardian riding with them; under 12s on a pillion seat (under 40 kg) or a pedal bike. A universal phone holder is fine. Stories are on by default. No GPX download.'],
                ['Beach ride (the North Shore)', 'Fat tyre e-Bikes only. Standard tyres bog down and get damaged.', 'Ferry is $2. The start time is set by the tide and the booking confirms it. No beach riding when the tide is above 1.3 m. A bike clean down charge applies. Never promise how far they will ride on the sand. A universal phone holder is fine.'],
                ['Bike On mountain bike rides', 'eMTB or dual suspension for the trail rides that need practised skills; hardtails and Kids MTB also suit the easier ones. The advanced trail ride needs a premium eMTB or dual suspension.', 'A Quad Lock is needed. Some trails are ridden descending only, so expect riders coming from above. Path sections are not licence exempt, so the e-Bike law applies there. Stories are off on Tewantin MTB Trails.'],
                ['Bike On gravel rides', 'Premium Gravel Bike recommended. Hardtails and hybrids also suit.', 'Stories are off by default. GPX download available.'],
                ['Bike On road rides', 'Premium BMC Road Bike recommended. Premium Gravel Bike also suits.', 'Moderate rides for confident riders. Road rules apply. Stories are off by default. GPX download available.'],
                ['By Earth and Ocean hinterland rides (mountain bike or gravel)', 'Bikes are not included: they bring their own or hire (Hardtail MTB $70, drop bar gravel bike $99, dual suspension MTB $99, premium e-mountain bike $200). MTB routes suit an MTB or e-MTB. Gravel routes suit a gravel bike or hardtail; on the rougher ones a hardtail or flat bar gravel bike gives more control than narrow gravel tyres.', 'Point to point: usually 9am at the shop (the booking confirms), we drive riders and bikes to the start and they ride one way back to the shop. Moderate fitness and previous gravel or MTB experience needed. Riders fix their own punctures and chains and navigate alone. Ages 18 and over, or younger with a parent or guardian. Quad Lock needed on MTB routes and strongly encouraged on rough gravel. Rough sections go soft, muddy or rutted after rain. Open the ride at the shop before the shuttle.']]),
            WARN('Mt Tinbeerwah One Way is used for the Summit to Sea e-Bike Tour, Self Guided, where we take riders to the start. It is not the Mt Tinbeerwah ride from the shop, which rides up and back. Summit to Sea riders use the premium e-Bike they booked.'),
            H('Good to know on every ride'),
            L('The riding time in the Ride Guide is pure riding at an easy pace for that kind of ride. Go by the time to allow on the booking, and bikes back by 4pm.',
              'Stories are off by default on road rides, gravel rides and Tewantin MTB Trails. Riders can turn on Point of interest stories in Settings.',
              '"Download this ride as a GPX file" (for a Garmin or Wahoo) is in Settings on road, gravel, MTB and hinterland rides, not the scenic e-Bike rides.',
              'Recovery during a self guided ride is charged from $75 per hour, one hour minimum, more for remote areas and the North Shore, with no guaranteed time.'),
        ]),
        ('When something goes wrong', [
            T('The common problems customers have with the Ride Guide, and the fix for each. Most can be sorted at the counter before they leave, or over the phone.'),
            TAB(['Problem', 'Fix'], [
                ['The QR code won\'t scan', f'Hold the phone 20 to 30 cm away in good light, using the normal camera app. Still no luck? Use the link in their booking email, or go to {SITE} and type the ride\'s route code (in Setting a customer up).'],
                ['"That code doesn\'t match a route."', 'Check the code against Setting a customer up (6 letters and numbers). If it says "Opening a new route needs signal", they need reception for the first open.'],
                ['It opened inside another app, or in a private tab', 'It works while that tab stays open, but nothing is kept once it closes. Open the link again in the normal browser (Safari or Chrome).'],
                ['"The start of the route is ... away. Head to the green marker."', 'Nothing is wrong. They are not on the route line yet, and directions start once they reach it. On hinterland rides this is normal until the shuttle drops them at the start.'],
                ['Directions or voice stopped', 'The phone was locked or they switched apps. Unlock it and go back to the Ride Guide tab: it warns them and carries on. Keep the screen on the whole ride, and use Battery saver, not the lock button.'],
                ['No voice', 'Turn the volume up, check the phone isn\'t connected to Bluetooth headphones or a car, check the voice button on the riding screen is on, and check Spoken directions is on in Settings.'],
                ['Location not allowed, or the blue dot doesn\'t move', 'iPhone: Settings > Privacy and Security > Location Services > Safari Websites > While Using. Android: in Chrome, tap the icon left of the address > Permissions > Location > Allow. Then reload the ride.'],
                ['"You\'re off the route" while stopped for a coffee or a swim', 'Tap Pause. Directions and warnings stop until they tap Resume.'],
                ['They really are off route', 'The Ride Guide doesn\'t give directions back. They use the map to get back to the route line, and it says "Back on route" when they rejoin.'],
                ['"You may be riding the route backwards."', 'Check the arrows on the route line and turn around.'],
                ['A turn called slightly early or late, or two directions at once', 'Follow the map and the "turn here" call at the junction. Tell a manager the ride name and the spot so it can be fixed in Ride with GPS.'],
                ['Closed the browser and lost the ride', f'Open {SITE} in the same browser and it is still there. Or tap the link in their booking email again, or type the route code (shown under "Getting back to this route"; we can read it to them over the phone from Setting a customer up). Adding it to the home screen keeps it safe. iPhone Safari can drop it if the site isn\'t opened for about 7 days.'],
                ['No signal on the ride', 'The route, map, voice and stops keep working if the ride was opened with signal first. The satellite map needs signal, and "More about this place" waits until signal is back.'],
                ['Phone battery draining', 'Turn on Battery saver in Settings: the map blacks out between turns, the voice carries on and the screen wakes before each turn. Start with a full charge. If needed, hire our phone with a Quad Lock mount ($40 a day).'],
                ['Phone mount isn\'t secure', 'A universal mount is fine on sealed paths and the North Shore ride. Off road (MTB rides, rough gravel) they need a Quad Lock: a Quad Lock mount is $5 per booking for riders who have a Quad Lock case. Without a case, hire our phone with a Quad Lock mount.'],
                ['Riding time on screen is different to what we told them', 'The Ride Guide\'s figure is time on the bike only, at an average speed for that kind of ride. The time we sell includes stops and breaks, so it is longer. Go by the time to allow and the 4pm return.'],
                ['Stop stories didn\'t play', 'Stories are off by default on road rides, gravel rides and Tewantin MTB Trails. Turn on Point of interest stories in Settings. On any stop card, Listen reads the short version and "Hear the full story" plays the longer one.'],
                ['The offer screen doesn\'t work at Land and Sea Brewery', 'The brewery needs the physical voucher card from us (one per rider, 18 and over). Give it out when they get back. Fliteschool Noosa: they call 0477 418 419 and mention Bike On.'],
                ['The finish card didn\'t come up', 'It only appears once most of the ride (75%) has been ridden on that phone, so a ride cut short or started on another phone won\'t show it. Tap End ride. Nothing else is needed.'],
                ['Wants the route on a Garmin or Wahoo', 'On road, gravel, MTB and hinterland rides, Settings has "Download this ride as a GPX file". Not on the scenic e-Bike rides.'],
                ['Wrong language, or wants miles', 'Use the EN and km buttons on the ride page, or Settings. Nine languages.'],
                ['Something on a ride is wrong (a closed path, a wrong story, an old photo)', 'Tell a manager. They change it on the Ride Desk or in Ride with GPS (EO-HI-10.1).'],
                ['Anything else', '"Need help? Call us" on the ride page rings the shop. Recovery during a self guided ride is charged from $75 per hour, one hour minimum, more for remote areas and the North Shore, with no guaranteed time.']]),
        ]),
    ]


def part2(D10, D10_2):
    return [
        ('Who changes what', [
            T('Every piece of information about a ride has one master: the one place it is changed. Everything else (the app, the ride sheets, the booklet, the iPad, EO Crew, the blogs) is a copy that follows by itself, usually within the hour (the next morning after 8pm).'),
            TAB(['To change', 'Change it in', 'Shows up'], [
                ['A ride\'s description', 'Its card on the Ride Desk', 'Ride Guide and EO Crew within about 10 minutes of Save; ride sheet and booklet within the hour'],
                ['Title, category, sell line, highlights, level, surface, bike, note on the sheet', 'Its card on the Ride Desk', 'Ride sheet, booklet and iPad within the hour'],
                ['The photo on the ride sheet and in the booklet', 'Its card on the Ride Desk (Photo)', 'Within the hour'],
                ['Staff notes (who it suits, not for, time to allow, sold as, bikes, start and finish)', 'Its card on the Ride Desk (For staff)', 'EO Crew within about 10 minutes of Save'],
                ['Whether a ride is in the app, on the iPad and in the booklet', 'Its card on the Ride Desk (Where it shows)', 'Within about 10 minutes of Save; sheets within the hour'],
                ['Name in the app, brand, type, stories on or off, GPX download', 'Its card on the Ride Desk', 'Within about 10 minutes of Save'],
                ['A place\'s story (the short overview, the full spoken story, the blog section)', 'The Story Library (ask Claude, or EO-HI-10.2)', 'App within minutes of the change being saved; blogs and pins the same day'],
                ['Which places a ride passes, and caution stops', 'Ride with GPS, the POI Library', 'Within the hour (hourly rebuilds 6am to 8pm)'],
                ['The route line and the turn directions', 'Ride with GPS, the route editor', 'Within the hour'],
                ['Distance, climbing and riding time', 'Nothing to change: worked out from the route line and the riding speed for the ride\'s type', 'With the line'],
                ['The riding speed for a kind of ride', 'The Ride Desk, Riding time estimates', 'Within about 10 minutes of Save'],
                ['Partner offers', 'The Ride Desk, Partner offers', 'Within about 10 minutes of Save'],
                ['When turns are announced, off route warnings, stop pop-ups, battery saver', 'The Ride Desk, rider settings', 'Within about 10 minutes of Save'],
                ['How a place name is said aloud', 'Ask Claude (EO-HI-10.2: the speech file)', 'Next build'],
                ['A new ride', 'Draw it in Ride with GPS (By Earth and Ocean organisation account)', 'On the Ride Desk as New, hidden by the next morning'],
                ['Brand colours, logos, phone numbers, review links', 'Ask Claude (EO-HI-10.2)', 'Next build']]),
            NOTE(f'The Ride Desk: {DESK}. Only people with edit access can change it (Ben, and anyone he shares it with as an editor); everyone else sees it read only.'),
        ]),
        ('The Ride Desk', [
            T('The Ride Desk is one page for every ride: a card per ride, the partner offers, and the rider settings. It is a claude.ai page, so open it while signed in to claude.ai. Nothing goes live until you press Save at the bottom.'),
            SHOTS('desk'),
            H('What is on a ride card'),
            TAB(['Section', 'What it holds'], [
                ['Where it shows', 'Live in the Ride Guide (off: the ride\'s link, QR code and route code stop working). Show on the hire desk iPad and in the booklet (off for private guide rides: no ride sheet, not in the booklet or EO Crew\'s customer lists, but staff still see its notes).'],
                ['In the Ride Guide app', 'Name in the app, brand (Bike On or By Earth and Ocean: the logo and colours on the map, and which half of the booklet it goes in), type (sets the riding speed), stories on or off by default, and whether riders can download a GPX file.'],
                ['Ride description', 'The master copy of the ride\'s story: its Ride Guide page, its ride sheet and EO Crew. The description in Ride with GPS is no longer the master: it is only shown while the card\'s description is empty.'],
                ['Ride sheet, iPad and booklet', 'Title, category, sell line, four highlights, level, surface, terrain (optional), recommended bike, the note on the sheet, and the photo.'],
                ['For staff', 'Who it suits, not for, time to allow, sold as, bikes to hire, start and finish, staff notes. Shown to staff in EO Crew; never on the public site.'],
                ['Worked out from the route', 'Distance, climbing and riding time, and how many times the ride has been ridden. Read only.'],
                ['Places the ride passes', 'Every place in ride order with the story told there, and a link to it in the Story Library. Read only: places are set in Ride with GPS and words in the Story Library.'],
                ['Link, route code and QR code', 'The customer link, route code and QR code, and a staff check link (below).']]),
            H('Saving'),
            S('Change anything on any card, the offers or the settings. The page marks what has changed and how many cards are not saved.',
              'Press Save. Every change on the page is saved at once.',
              'The status at the top shows "Saved. Updating the live site", then "Live on the site", usually within 10 minutes.',
              'A ride switched on must have a name in the app, a brand and a type, or Save stays greyed out and says why.'),
            NOTE('Undo changes throws away anything not saved yet. If two people change the same card, the page keeps your unsaved changes and shows the other person\'s saved ones on the cards you haven\'t touched.'),
            H('The staff check link'),
            T('Each card has a staff check link (Link, route code and QR code, then Staff check link). It opens the ride in check view: Next and Back step through every direction, warning and stop, a red ring shows where each one is, and each is spoken. Use it to check a ride after changing it in Ride with GPS. Check view never counts as a ride and isn\'t for customers.'),
        ]),
        ('Changing a ride', [
            H('The description, or the sheet words'),
            S('Open the Ride Desk and find the ride (search, or the filters at the top).',
              'Open its card and change the Ride description, or the Title, Sell line, Highlights and so on.',
              'Press Save. The app has the new words within about 10 minutes; the ride sheet and booklet are rebuilt within the hour.'),
            NOTE('House style applies everywhere: no dashes between words, e-Bike, and the Product Truth for anything about safety, prices or products.'),
            H('The photo in the booklet'),
            S('Open the ride\'s card and go to Photo.',
              'Choose one: The photo on its Bike On website page (the default), One of the ride\'s own photos (photos of its stops, to pick from), Upload a photo (it is shrunk to a sensible size), or A link to a photo.',
              'Press Save. The new photo is on the ride sheet, the iPad and in the booklet within the hour.'),
            T(f'A ride with no photo shows a placeholder, and the weekly check puts it on Ben\'s Desk until one is chosen. Reprint that page of the booklet afterwards: the Rides tab lists the pages that changed. [Open Rides]({BOOKLET})'),
            H('Staff notes'),
            S('Open the ride\'s card and go to For staff.',
              'Fill in who it suits, who it isn\'t for, time to allow, what it is sold as, bikes to hire, start and finish, and anything staff must know.',
              'Press Save. EO Crew shows them in Our rides (EO-HI-10) within about 10 minutes.'),
            H('Taking a ride out, or putting it back'),
            L('Switch off Live in the Ride Guide: the ride leaves the app and its link, QR code and route code stop working. Switch it back on and the same link and code work again.',
              'Switch off Show on the hire desk iPad and in the booklet: the ride stays in the app (for private guide rides) but has no sheet, isn\'t in the booklet and isn\'t offered to customers in EO Crew.'),
            H('Brand, type, stories and GPX'),
            L('Brand: the logo and colours on the map, the review links on the finish card, and which half of the booklet the ride sits in.',
              'Type (scenic, mountain bike, gravel, road, hinterland mountain bike, hinterland gravel): picks the riding speed for its riding time.',
              'Point of interest stories on by default: riders can still change it on their phone.',
              'GPX download: lets riders download the route line for a bike computer.'),
            H('Changing a ride\'s link and QR code'),
            T('Only when a link has been shared somewhere it shouldn\'t be. Ask Claude to change the ride\'s link: the old link, QR code and route code stop working at once, and every customer with the old one is cut off. Reprint the ride\'s page of the booklet.'),
        ]),
        ('New rides', [
            T('A new ride starts in Ride with GPS. Every route in the By Earth and Ocean organisation account appears on the Ride Desk by itself, as a card marked New, hidden, by the next morning.'),
            S('Draw the ride in the By Earth and Ocean organisation account on Ride with GPS, with its turn directions (cue text is spoken word for word) and its places (POI Library pins). Set its sharing to "Allow anyone with the link to view".',
              'Next morning, open the Ride Desk and use the New filter. The card has the ride\'s name and its Ride with GPS description to start from.',
              'Fill in the card: name in the app, brand, type, description, sheet words, photo and staff notes.',
              'Switch on Live in the Ride Guide (and Show on the hire desk iPad if it is one we offer), then Save.',
              'Ask Claude to add the ride\'s map labels for its ride sheet and to check its stops have stories. Its sheet is in the booklet the next morning.'),
            NOTE('A new ride left hidden for more than 14 days goes on Ben\'s Desk with the question "Switch it on, or keep it hidden?". Routes that aren\'t rides (a kayak tour, a test) can simply stay hidden.'),
        ]),
        ('Stories, places and stops', [
            T('Where a ride stops, and what is said there, come from two places.'),
            TAB(['Thing', 'Where it lives', 'How to change it'], [
                ['Which places a ride passes, and where on the ride', 'Ride with GPS, the By Earth and Ocean POI Library. A library pin can be added to many rides; editing it changes it on every ride.', 'Add or move the pin in the POI Library, and add it to the rides that pass it.'],
                ['The words: the short overview read on arrival, the full spoken story and the blog section', f'The Story Library: one entry per place, read it at {LIB}', 'Ask Claude to change the story. Claude keeps the spoken story, the pin line and both blogs in step.'],
                ['A caution stop (a busy crossing, a slippery path)', 'A Ride with GPS pin with the Caution icon', 'Add it in Ride with GPS. Its name is the warning that is spoken.'],
                ['Toilets, cafes, water, parking', 'Ride with GPS pins with those icons', 'They show on the map and in the Stops list only, never pop up. Toilets are left out altogether.']]),
            L('What a pin does depends on its Ride with GPS icon: Caution is a warning; General Info, Viewpoint, Summit, Monument, Park, Swimming, Camping, Trailhead, Ferry, Library and Start pop up and are read; facility icons only show on the map; the Finish flag makes the finish card.',
              'A stop about a building only goes where riders can see it from the route.',
              f'A change of fact (a date, a name, a claim) goes to Ben first, on the Ride Story Review page ({REVIEW}). Until he rules, the app keeps the agreed words.',
              'The Ride Desk card shows each place in ride order with the story told there, and a link to its Story Library entry.'),
        ]),
        ('Route line, directions and distance', [
            T('The route line and every turn direction are drawn in Ride with GPS, in the By Earth and Ocean organisation account. The Ride Guide copies them every hour from 6am to 8pm and at 3am, so a fix is live within the hour.'),
            L('Turn directions (cues) are spoken word for word. Write them as full sentences: "Turn left onto Gympie Terrace."',
              'A cue marked Danger is a caution: said earlier, with "Caution." first.',
              'Distance and climbing come from the line. Riding time is the distance at the riding speed for the ride\'s type (set on the Ride Desk under Riding time estimates).',
              'A ride that suddenly loses a third of its stops in Ride with GPS keeps its last good copy and is flagged, in case the change was a mistake.',
              'Check a changed ride with the staff check link on its card.'),
            WARN('Every ride must be shared as "Allow anyone with the link to view" in Ride with GPS, or the Ride Guide can\'t read it and keeps its last good copy.'),
        ]),
        ('Partner offers', [
            T('Offers are set on the Ride Desk under Partner offers, then Save.'),
            TAB(['Field', 'What it does'], [
                ['When riders see it', 'Anywhere on the ride (pops up near the partner), or Near the end only (comes up in the last 1.5 km and on the finish card).'],
                ['Partner, deal, second deal, about', 'What the offer card says.'],
                ['How to claim, conditions', 'How riders claim it, and the fine print (one condition per line).'],
                ['Phone, website', 'Call and Visit buttons on the card.'],
                ['Where', 'An address or a Google Maps link. The Ride Guide works out the spot; the page says if it couldn\'t.'],
                ['Pop-up distance', 'How close the rider gets before it pops up.'],
                ['Show on every map, leave off chosen maps', 'Which rides show it. Otherwise it shows on every ride passing within the pop-up distance.'],
                ['End date', 'Hidden after this date.'],
                ['On or off', 'Turn an offer off without deleting it.']]),
            NOTE('Partner logos are added by Claude. Land and Sea Brewery needs our physical voucher card, so its card tells riders to collect it from us.'),
        ]),
        ('Rider settings the phone can\'t change', [
            T('These are set once, for every rider, on the Ride Desk. Each one has a slider with the recommended value marked and an example of what riders hear. The values in use today are on the Ride Desk itself.'),
            TAB(['Group', 'Settings', 'What they decide'], [
                ['Spoken turn directions', 'Early warning before a turn; Turn now; Turns close together; Skip the early warning between quick turns; Early warning for caution cues', 'How far before a turn the rider first hears about it, when the turn itself is said, when two close turns are joined ("Then ..."), and how early a caution is said.'],
                ['Going off route', 'Counts as off route; Wait before warning; Repeat the warning every', 'How far from the line counts as off route, how many seconds of readings before the warning, and how often it repeats.'],
                ['Stops', 'Open a stop when the rider is within; Warn about caution stops this far ahead', 'When a stop pops up, and how early a caution stop is warned about.'],
                ['Screen', 'Battery saver; Point of interest stories for a new ride; Battery saver lights up before a turn; Battery saver blacks out after', 'What riders start with (they can change it on the phone), and how battery saver behaves.'],
                ['Riding time estimates', 'One average speed per kind of ride', 'The riding time on every ride page and while riding. Time on the bike only.']]),
            NOTE('Every value is checked again when the site builds: one out of range falls back to its default, so a slip can\'t break the app. Recommended rider settings puts our recommended values back (press Save to use them). A rider who changed a setting on their own phone keeps their choice.'),
        ]),
        ('Ride sheets, the booklet and QR cards', [
            T(f'Every ride on the hire desk iPad has an A4 ride sheet: a 3D map of the route with its place names, the photo, the description, distance, climbing, riding time, level, surface, bike, a height profile and the QR code with its route code. The sheets for both brands, with a cover each, make up the rides booklet. [Open the ride sheets and the whole booklet]({BOOKLET})'),
            L('The sheets rebuild themselves after every change on the Ride Desk or in Ride with GPS, usually within the hour. The 3D map is only redrawn when the route line changes a lot, and that can take until the next morning.',
              'Managers see a yellow box on the Rides tab listing the pages that changed since the counter booklet was printed. Reprint those pages, then tap Pages reprinted.',
              'A sheet that fails its own checks (a QR code that doesn\'t scan, a wrong route code) is held back and the ride keeps its previous sheet.',
              'The sheets carry each ride\'s private QR code, so they are only ever opened through EO Crew.',
              'QR codes and route codes for every ride are also in EO-HI-10, Setting a customer up, always current.'),
        ]),
        ('Ride counts', [
            T('Each ride card shows how many times it has been ridden (and in the last 30 days) and on how many phones it was opened, with a total at the top of the Rides section. Counting started on 17 October 2026.'),
            L('Opened: the first time a ride is opened on a phone. Ridden: the finish card came up (75% of the ride ridden on that phone).',
              'Nothing about the rider is sent: only the ride, the date and a random number.',
              'Indicative only: clearing the browser counts as a new phone, and two people on one phone count as one ride. Staff check links never count.'),
        ]),
        ('What the Ride Guide can\'t do', [
            T('These are limits of a web page on a phone, not faults. Staff should know them so customers do.'),
            TAB(['Limit', 'What it means', 'What we do about it'], [
                ['It can\'t speak with the phone locked', 'A web page stops when the screen locks or the rider switches apps. Directions and GPS stop too.', 'The screen stays on during a ride by itself, the ride page and the start of every ride say so, and Battery saver saves power instead.'],
                ['It doesn\'t give directions back to the route', 'Off route, it says how far away the line is, not how to get there.', 'Riders use the map. It says "Back on route" when they rejoin.'],
                ['Saved rides can be cleared', 'Clearing browsing data, a private tab, or (iPhone Safari) not opening the site for about 7 days removes saved rides.', 'The route code and the booking email link always get them back. Adding the ride to the home screen keeps it safe.'],
                ['Some things need signal', 'The first open of a ride, satellite view and "More about this place".', 'Open the ride at the shop and wait for "Saved to your phone".'],
                ['Real screen brightness can\'t be changed', 'A web page can\'t dim the screen.', 'Battery saver blacks the screen out instead (almost no power on modern phones).'],
                ['Riding time is time on the bike', 'It is distance at an average speed for that kind of ride.', 'Go by the time to allow on the booking.'],
                ['GPS can wander', 'Near trees, cliffs and tall buildings the dot can drift 10 to 20 metres.', 'Single track sections allow more room before "off route".'],
                ['It needs a phone in a mount', 'Holding a phone while riding isn\'t safe.', 'Universal holder on sealed paths, Quad Lock off road, or our navigation phone.']]),
        ]),
        ('Checks that run by themselves', [
            T(f'The Ride Guide checks itself. Anything that needs a person goes on Ben\'s Desk ({BEN_DESK}) as a card with one question; nothing is emailed.'),
            TAB(['When', 'What is checked', 'If something is wrong'], [
                ['Every build (hourly 6am to 8pm, and 3am)', 'Every ride read from Ride with GPS, stops, offers, links, translations, the Ride Desk cards.', 'A ride that can\'t be read keeps its last good copy. Problems are listed in the health report (EO-HI-10.2).'],
                ['When you press Save on the Ride Desk', 'That the change reached the live site.', 'The Ride Desk status says so, and a card goes on Ben\'s Desk.'],
                ['Every night', 'New routes in Ride with GPS, ride counts, photo previews.', 'New routes become New, hidden cards.'],
                ['Every week (the Drift Check Register)', 'Every QR code and route code opens its ride, every link and photo works, nothing is untranslated, the stories match the Story Library, every Ride Desk card matches what the app shows, and these manuals still match the app.', 'Fixed by itself where it can. Otherwise one card per problem on Ben\'s Desk: for example cards with empty fields, rides with no photo, or a new ride left hidden for over 14 days.']]),
        ]),
    ]


def part3():
    return [
        ('How it fits together', [
            T('The Ride Guide is a plain website. There is no server and no database behind the app: GitHub builds the website from our information and hosts it free, and each rider\'s phone does all the work (GPS, voice, off route). That is why it costs nothing to run and can\'t go down under load.'),
            TAB(['Part', 'What it is', 'Where'], [
                ['The app (what riders open)', 'A website on GitHub Pages', f'https://{SITE}/'],
                ['The code and the settings files', 'A public GitHub repository (it holds no keys or private links)', REPO],
                ['The build', 'GitHub Actions: rebuilds the website from Ride with GPS, the Ride Desk and the Story Library', f'{REPO}/actions'],
                ['The Ride Desk', 'A claude.ai page with its own small database', DESK],
                ['Routes, turns and places', 'Ride with GPS, By Earth and Ocean organisation account', 'https://ridewithgps.com/organizations/15663-by-earth-and-ocean'],
                ['Stories', 'The Story Library: files in the repository', LIB],
                ['Natural voice', 'Google Cloud Text-to-Speech, project "Ride Guide Voice"', 'https://console.cloud.google.com (admin@elementoutdoors.com.au)'],
                ['Maps', 'OpenFreeMap (standard), Esri World Imagery (satellite)', 'Free services, no account'],
                ['Ride counts', 'A Google Apps Script and the Google Sheet "Ride Guide ride counts"', 'admin@elementoutdoors.com.au'],
                ['Staff side', 'EO Crew (Base44), which opens the locked staff files', 'https://element-crew-connect.base44.app'],
                ['Automatic jobs', 'Claude scheduled tasks and Ben\'s Desk', BEN_DESK]]),
            H('How a change reaches a rider\'s phone'),
            S('Someone changes something at its master: a turn in Ride with GPS, a card on the Ride Desk, a story in the Story Library.',
              'Ride Desk changes: Save starts the scheduled task "Ride Guide settings apply", which copies the cards and settings into the repository\'s config files and saves them to GitHub.',
              'Saving to GitHub (or the hourly timer, 6am to 8pm, and 3:07am) starts the build. It reads every live ride from Ride with GPS, adds the Ride Desk card, stories, offers, translations and voice recordings, and publishes the website. About 3 to 5 minutes.',
              'After the website, the build makes the ride sheets and booklet and retakes the screenshots for these manuals.',
              'Phones pick up the new version the next time the ride is opened with signal and no ride is under way. Nothing changes under a rider mid ride.'),
        ]),
        ('Where every piece of information lives', [
            T('One master for each thing. The files are in the repository; the "Changed by" column says how they are meant to change.'),
            TAB(['Information', 'Master', 'File in the repository', 'Changed by'], [
                ['Route line, turns, places a ride passes', 'Ride with GPS', 'None (read every build; last good copy kept in the Actions cache)', 'Anyone in Ride with GPS'],
                ['Ride card: live, iPad, brand, type, stories, GPX, name, description, sheet words, photo', 'Ride Desk', 'config/ride-desk.json', 'The settings task, from the Ride Desk'],
                ['Staff notes and Ride with GPS privacy codes', 'Ride Desk', 'config/ride-desk-private.enc.json (locked)', 'The settings task only (it is locked)'],
                ['Uploaded ride sheet photos', 'Ride Desk', 'config/ride-photos/', 'The settings task'],
                ['Rider settings (timings, battery saver, speeds)', 'Ride Desk', 'config/settings.json', 'The settings task'],
                ['Partner offers', 'Ride Desk', 'config/offers.json', 'The settings task (logos: site/assets/)'],
                ['Place stories, blog sections, pin lines', 'Story Library', 'library/places/<place>.json (config/stories.json and config/place-record.json are made from it)', 'Claude, or by hand (Changing things without Claude)'],
                ['How words are said aloud', 'Claude', 'config/speech.json', 'Claude, or by hand'],
                ['Translations', 'Claude (the weekly check)', 'config/i18n/<language>.json', 'The weekly check'],
                ['Brands: colours, logos, phone, review links, feedback email', 'Claude', 'config/brands.json, site/assets/', 'Claude, or by hand'],
                ['Ride sheet map labels and camera angle', 'Claude', 'ride-sheets/rides.py', 'Claude'],
                ['Voice settings and the monthly cap', 'Claude', 'config/voice.json', 'Claude'],
                ['The app itself', 'Claude', 'site/ (app.js, app.css, index.html)', 'Claude'],
                ['The Ride Desk page', 'Claude', 'ride-desk/ (built into ride-desk/ride-desk.html, then published to the claude.ai page)', 'Claude'],
                ['Customer links and route codes', 'Made from a secret salt and each ride\'s number', 'Never in the repository; on the Ride Desk and in EO Crew only', 'Claude (by bumping a ride\'s rev)']]),
            WARN('The settings task copies the Ride Desk into config/ride-desk.json, config/settings.json and config/offers.json. A hand edit to those files is overwritten the next time the Ride Desk is saved or the task runs at night, unless the same change is made on the Ride Desk.'),
        ]),
        ('The website and the code', [
            L(f'The app: https://{SITE}/ (GitHub Pages, free). Each ride lives at a secret address; the home page alone shows nothing.',
              f'Health report: https://{SITE}/health.json. When it was built, every ride and where its data came from, and any problems. The first place to look when something is wrong.',
              f'Story Library to read: {LIB}. Place names to check by ear: https://{SITE}/listen.html',
              f'Code: {REPO} (public: anyone can read it; only the elementoutdoors GitHub account, and Claude through it, can change it).'),
            TAB(['Folder or file', 'What it holds'], [
                ['site/', 'The app: index.html, app.js (everything it does), app.css (how it looks), sw.js (saving to the phone for offline use)'],
                ['scripts/build.mjs', 'The build: reads Ride with GPS, adds everything else, writes the website into dist/'],
                ['scripts/ride-desk.mjs', 'Ride Desk plumbing: copy cards in, lock staff notes, publish numbers and places back, find new rides, check'],
                ['scripts/check.mjs', 'The weekly check'],
                ['scripts/voice.mjs', 'Records the natural voice'],
                ['scripts/staff_screens.py, scripts/staff_bundle.mjs', 'The screenshots for these manuals, and locking files for EO Crew'],
                ['scripts/manual_facts.mjs, manual/', 'How these manuals keep up with the code'],
                ['config/', 'Every setting and the ride cards (see Where every piece of information lives)'],
                ['library/', 'The Story Library (read library/README.md)'],
                ['ride-sheets/', 'The ride sheets and booklet (read ride-sheets/README.md)'],
                ['ride-desk/', 'The Ride Desk page source'],
                ['.github/workflows/build.yml', 'When and how the build runs'],
                ['README.md', 'How everything works, in more detail']]),
        ]),
        ('The build', [
            L('Runs at 3:07am Brisbane, every hour from 6:07am to 8:07pm, whenever anything is saved to the repository, and on demand.',
              f'Watch it: {REPO}/actions, "Build and publish". Green is good. Each run takes about 3 to 5 minutes, longer when the ride sheets are redrawn.',
              f'Run it by hand: {REPO}/actions, Build and publish, Run workflow.',
              'Steps: get saved voice recordings, build from Ride with GPS, keep new recordings, take the manual screenshots, make the ride sheets and booklet, check every route built, publish, then report problems.',
              'Safety nets: a ride Ride with GPS can\'t give us keeps its last good copy; a ride that suddenly loses a third of its stops keeps its last good copy; the sheets, booklet and screenshots keep their last good versions if they fail; a value out of range falls back to its default.',
              'Secrets it uses (GitHub, Settings, Secrets): ROUTE_SECRETS (the key salt and the first 29 rides\' Ride with GPS privacy codes) and GOOGLE_TTS_KEY (the voice). Only Ben pastes secrets.'),
        ]),
        ('The Ride Desk under the hood', [
            L(f'The page: {DESK}. A claude.ai page with its own database, owned by admin@elementoutdoors.com.au. Anyone it is shared with as an editor can change it.',
              'The page\'s source is in the repository (ride-desk/). After a change Claude rebuilds it and publishes it to the same address.',
              'Save writes the changed cards and settings to the page\'s database, then starts the scheduled task "Ride Guide settings apply".',
              'That task: copies the cards into config/ride-desk.json, locks the staff notes and privacy codes into config/ride-desk-private.enc.json, writes config/settings.json and config/offers.json, saves them to GitHub, waits for the build and confirms it is live, then writes "Live on the site" back to the page. It also runs nightly at 2:41am to catch up, refresh the numbers, places, photo previews, links and ride counts on the page, and look for new routes in Ride with GPS (in Chrome on bens-pc, where Ben is signed in).',
              'Locked data: staff notes and privacy codes are locked with keys only the build and the Ride Desk hold, so the public repository never shows them. Customer links come back to the page locked too.'),
            TAB(['Database area', 'Holds'], [
                ['rides', 'One card per ride'],
                ['settings', 'The rider settings and offers as saved (current), whether they are live (status), and which task Save starts (config)'],
                ['routes', 'Customer links and route codes (links), ride counts (counts), offers as live (offers)'],
                ['published', 'What the build worked out: numbers and places (rides), stories (stories), photo previews (thumbs)'],
                ['private', 'Ride with GPS privacy codes and the page\'s key. Only editors can read it.'],
                ['desk', 'When Ride with GPS was last checked for new routes (scan)']]),
        ]),
        ('Ride with GPS', [
            L('Account: the By Earth and Ocean organisation account (a Tour Account), organisation 15663. Ben\'s login; signed in on bens-pc.',
              'Collections used: Scenic Rides from Shop, Gravel Rides from Shop, MTB Rides from Shop, Road Rides from Shop, Hinterland MTB Rides Point to Point, Hinterland Gravel Rides Point to Point, plus Mt Tinbeerwah One Way. Any route in the account can become a ride.',
              'POI Library: https://ridewithgps.com/organizations/15663-by-earth-and-ocean/poi_library. Every stop is a library pin, tagged Bike On or By Earth and Ocean. Edit stops there, not on the ride.',
              'Each ride must be shared as "Allow anyone with the link to view". Private rides need their privacy code, which the Ride Desk holds (locked).',
              'Ride with GPS Experiences (what the old app used) need "Publish Updates" after a change; the Ride Guide doesn\'t.'),
        ]),
        ('The Story Library', [
            L(f'Every place story is written once, in library/places/ in the repository. Read them at {LIB}.',
              'Each entry holds the place\'s blog section for each brand, its Ride with GPS pin lines (read on arrival) and its full spoken story (about a minute).',
              'From it the build makes config/stories.json and config/place-record.json (never edited by hand), and EO Crew copies the stories daily.',
              'After a change, the blogs (bikeon.com.au and byearthandocean.com.au, through WordPress and Elementor) and the Ride with GPS pins are brought into line from Chrome on bens-pc. The weekly Story Library check puts back any difference.',
              f'A change of fact goes to Ben first on the Ride Story Review page ({REVIEW}).',
              'Full rules: library/README.md in the repository.'),
        ]),
        ('Voice, maps, photos and counts', [
            L('Natural voice: Google Cloud project "Ride Guide Voice" (ride-guide-voice) under admin@elementoutdoors.com.au, Chirp 3 HD voice "Aoede", in nine languages. Recordings are kept on the voice-cache branch of the repository and only new or changed lines are recorded. A monthly cap keeps it inside Google\'s free allowance (config/voice.json), and the budget alert "Ride Guide Voice monthly" emails at A$10 a month.',
              'Lines not recorded yet use the phone\'s own voice, so a voice problem never stops directions.',
              'Maps: OpenFreeMap tiles (free, no account, saved to the phone). Satellite: Esri World Imagery (needs signal).',
              'Stop photos load from Ride with GPS and are saved to the phone.',
              'Ride counts: the Apps Script project "Ride Guide ride counter", bound to the Google Sheet "Ride Guide ride counts" (admin@). Its address is in config/counter.json; its code copy is scripts/ride-counts.gs.'),
        ]),
        ('EO Crew and the locked files', [
            T('Route codes and links are never public, so everything staff see that carries them is published locked with EO Crew\'s public key. Only EO Crew\'s server can open them.'),
            TAB(['File on the site', 'What it is', 'Used in EO Crew'], [
                ['staff.enc.json', 'Every live ride\'s link, route code, title, iPad switch and staff notes', 'QR codes, Our rides'],
                ['staff-screens.enc.json', 'The screenshots in these manuals, retaken nightly', 'The pictures in EO-HI-10 and EO-HI-10.1'],
                ['booklet.pdf.enc and booklet.key.json', 'The whole rides booklet', 'Hire desk, Rides, Whole booklet'],
                ['ride-sheets/<ride>.enc.json, ride-sheets/index.enc.json', 'One sheet per ride, and the list of sheets', 'Hire desk, Rides'],
                ['rides.json (not locked: no codes)', 'Every iPad ride\'s description, numbers, stops and sheet words', 'Our rides, customer ride lists'],
                ['library.json, stories-voice.json (not locked)', 'The Story Library and its recordings', 'Know Noosa, wildlife, tour manuals']]),
            L('EO Crew\'s function rideGuide opens the files. Counts only, nothing private: https://element-crew-connect.base44.app/functions/rideGuide?check=1',
              'EO Crew\'s private key is the RideGuideKey record in EO Crew; its public half is config/staff-key.pem in the repository. To replace it: delete the RideGuideKey record, open https://element-crew-connect.base44.app/functions/rideGuide (EO Crew makes a new key and shows its public half), and copy that public key into config/staff-key.pem.'),
        ]),
        ('Scheduled tasks and Ben\'s Desk', [
            T(f'Automatic jobs run as Claude scheduled tasks on the admin@elementoutdoors.com.au Claude account. Anything that needs a person becomes a card on Ben\'s Desk ({BEN_DESK}).'),
            TAB(['Job', 'When', 'What it does'], [
                ['Build and publish (GitHub Actions, not Claude)', '3:07am, hourly 6am to 8pm, on every change', 'Builds and publishes the website, sheets, booklet and screenshots.'],
                ['Ride Guide settings apply', 'When Save is pressed on the Ride Desk, and 2:41am nightly', 'Copies the Ride Desk to GitHub, confirms it is live, refreshes the page, finds new routes. A failure makes the card "rg-settings-failed".'],
                ['Element Outdoors drift checks (weekly)', 'Weekly', 'Runs the Ride Guide routes check and the Story Library check from the Drift Check Register, fixes what it can, and cards the rest.'],
                ['Ben\'s Desk inbox (cloud) and Ben\'s Desk Chrome fixes (bens-pc)', 'Through the day', 'Carry out Ben\'s answers on Ben\'s Desk cards, including anything that needs Chrome on bens-pc.']]),
            NOTE('bens-pc is Ben\'s always-on Azure computer. Chrome on it is signed in to Ride with GPS, GitHub, WordPress, Base44 and Google, so jobs that need a website work there. If it is off, those jobs wait.'),
        ]),
        ('Accounts and logins', [
            T('Where each part is managed. No passwords are kept here or anywhere in the Ride Guide.'),
            TAB(['Service', 'Address', 'Signed in as', 'Used for'], [
                ['GitHub', REPO, 'The elementoutdoors GitHub account', 'Code, settings files, the build, the website, the secrets'],
                ['Ride with GPS', 'https://ridewithgps.com', 'Ben\'s login, with the By Earth and Ocean organisation', 'Routes, turns, POI Library'],
                ['claude.ai', DESK, 'admin@elementoutdoors.com.au', 'The Ride Desk, Ben\'s Desk, scheduled tasks'],
                ['Google Cloud', 'https://console.cloud.google.com', 'admin@elementoutdoors.com.au', 'Natural voice (project ride-guide-voice), billing and the budget alert'],
                ['Google Apps Script and Sheets', 'https://script.google.com', 'admin@elementoutdoors.com.au', 'Ride counts'],
                ['Base44', 'https://app.base44.com', 'The EO Crew owner account', 'EO Crew, which shows the manuals, QR codes and booklet'],
                ['WordPress', 'bikeon.com.au/wp-admin and byearthandocean.com.au/wp-admin', 'Ben\'s logins', 'The two ride story blogs'],
                ['bens-pc', 'Chrome Remote Desktop', 'Ben', 'The always-on computer whose Chrome the jobs use']]),
        ]),
        ('Secrets and keys', [
            TAB(['Secret or key', 'Kept in', 'What it does', 'If it is lost or leaked'], [
                ['ROUTE_SECRETS', 'GitHub, repository Settings, Secrets', 'The key salt (makes every ride\'s secret address and route code, and the build\'s own key) and the first 29 rides\' privacy codes', 'Changing the salt changes every link and route code: every QR code must be reprinted. Only Ben pastes it.'],
                ['GOOGLE_TTS_KEY', 'GitHub, repository Settings, Secrets', 'Lets the build record the natural voice (Text-to-Speech only)', 'Make a new key in Google Cloud and paste it; the old one can be deleted there.'],
                ['EO Crew key', 'EO Crew (RideGuideKey record); public half config/staff-key.pem', 'Locks and opens the staff files', 'See EO Crew and the locked files.'],
                ['Ride Desk key', 'The Ride Desk database (private); public half config/ride-desk-key.json', 'Opens the customer links on the page', 'Claude makes a new one.']]),
            MUST('Never paste a secret, key, private link or route code into the repository, a public page, an email or a chat with someone outside the business. The repository is public.'),
        ]),
        ('Changing things without Claude', [
            T('Everything can be done by hand on github.com while signed in as elementoutdoors. Each saved change starts a build, live in about 5 minutes.'),
            H('Edit a file on GitHub'),
            S(f'Open {REPO} and click through to the file (for example config/settings.json).',
              'Click the pencil (Edit this file). Change only what you need; keep the quotes, commas and brackets exactly as they are.',
              'Click Commit changes, write what you changed, and commit straight to main.',
              f'Watch the build at {REPO}/actions. Red means it failed: open it to see why, or undo the change (below).',
              f'Check https://{SITE}/health.json: "built" is the new time and "problems" is empty.'),
            H('Common jobs by hand'),
            TAB(['Job', 'How'], [
                ['Rebuild now', f'{REPO}/actions, Build and publish, Run workflow.'],
                ['Undo a bad change', 'Open the commit (repository, Commits), then Revert, or edit the file back. A build follows.'],
                ['Change a rider setting or offer while the settings task isn\'t working', 'Edit config/settings.json or config/offers.json, and make the same change on the Ride Desk so it isn\'t overwritten later.'],
                ['Change a ride\'s description or sheet words while the settings task isn\'t working', 'Edit that ride in config/ride-desk.json, and make the same change on its Ride Desk card.'],
                ['Take a ride out of the app in a hurry', 'In config/ride-desk.json set that ride\'s "live" to false. Also switch it off on its Ride Desk card.'],
                ['Change a story', 'Needs a computer with Node.js: download the repository, edit library/places/<place>.json, run "node scripts/library.mjs lint" and "node scripts/library.mjs generate", then save all changed files to GitHub. Then update the blog section in WordPress and the pin in Ride with GPS to match.'],
                ['Change how a name is said', 'Add it to "names" in config/speech.json, written the way it should sound.'],
                ['Change a phone number, review link or colour', 'config/brands.json.'],
                ['Staff notes', 'Can\'t be changed by hand: they are locked. Change them on the Ride Desk; they reach EO Crew when the settings task next runs.']]),
            WARN('Hand edits to config/ride-desk.json, config/settings.json and config/offers.json are replaced by the Ride Desk the next time it is saved or the task runs at night. Always make the same change on the Ride Desk.'),
        ]),
        ('When something goes wrong', [
            TAB(['What you see', 'Look at', 'Usual fix'], [
                ['A ride shows old information', f'health.json: that ride\'s "source" (live or a last good copy) and "built"', 'Ride with GPS couldn\'t be read: check the ride\'s sharing is "anyone with the link", then rebuild.'],
                ['The Ride Desk says it is still updating after an hour', f'Ben\'s Desk card rg-settings-failed; {REPO}/actions', 'Ask Claude to run "Ride Guide settings apply", or press Save again.'],
                ['Every ride is down', f'https://{SITE}/ and {REPO}/actions', 'A failed publish keeps the last good website, so this is rare: rerun the build, or revert the last change.'],
                ['No voice, or the phone\'s voice instead of ours', 'health.json "voice"', 'New lines wait for the monthly cap or for translation; the phone\'s voice covers them. Nothing to do unless it lasts more than a month.'],
                ['A turn is said in the wrong place', 'The staff check link on the ride\'s card', 'Move the cue in Ride with GPS.'],
                ['QR codes, screenshots or the booklet missing in EO Crew', 'https://element-crew-connect.base44.app/functions/rideGuide?check=1', 'If it says the key is wrong, see EO Crew and the locked files. Otherwise rerun the build.'],
                ['New routes aren\'t appearing on the Ride Desk', 'The Ride Desk desk/scan date; bens-pc is on and signed in to Ride with GPS', 'Turn bens-pc on, or sign in to Ride with GPS in its Chrome.'],
                ['A story is wrong', f'{LIB}', 'Ask Claude to change it in the Story Library.']]),
            NOTE('If a build fails, the website stays as it was. Riders are never left without a ride because of a failed change.'),
        ]),
        ('Running costs and limits', [
            L('GitHub Pages and GitHub Actions: free for a public repository. The site is a few hundred KB plus the voice recordings, well inside the 1 GB limit, and about 1,000 to 2,000 riders a day before GitHub\'s soft traffic limit would matter.',
              'No limit on riders at once: each phone does its own work.',
              'Google Text-to-Speech: inside the free monthly allowance, plus approved Google Cloud credit, with the A$10 budget alert as a backstop.',
              'OpenFreeMap and Esri: free. OpenFreeMap is run on donations with no uptime promise; riders already have the map saved once a ride is opened.',
              'Base44 (EO Crew) and Claude are paid subscriptions of their own.'),
        ]),
        ('How these manuals stay up to date', [
            L('The pictures are retaken every night by the build (scripts/staff_screens.py), on a real ride with a simulated GPS and on the Ride Desk with made-up data, so they always show the app as it is.',
              'The QR codes, route codes, ride list and staff notes in EO-HI-10 are read live.',
              'The words are checked weekly: scripts/manual_facts.mjs reads the settings, buttons, wording, Ride Desk sections and build steps from the code and compares them with what these manuals were written against (manual/written.json). Anything changed is rewritten in these manuals by the weekly check, then recorded.',
              'A change to the Ride Guide from any chat goes through the same repository, so the check sees it wherever it was made.'),
        ]),
    ]


if __name__ == '__main__':
    print(json.dumps({'part1': part1('D10_1', 'D10_2'), 'part2': part2('D10', 'D10_2'), 'part3': part3()}, indent=1))
