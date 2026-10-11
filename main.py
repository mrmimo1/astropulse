"""AstroPulse: private multi-user daily reflection digest. Python 3.12, stdlib only."""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

METHOD = 'ank-jyotish-reduce-all-calendar-year-v1'
LABELS = {'en': ['Mulank', 'Bhagyank', 'Personal year', 'Personal month', 'Personal day', 'Universal day'], 'bn': ['মূলাঙ্ক', 'ভাগ্যাঙ্ক', 'এ বছরের সংখ্যা', 'এ মাসের সংখ্যা', 'আজ আপনার সংখ্যা', 'আজকের সবার সংখ্যা'], 'hi': ['मूलांक', 'भाग्यांक', 'व्यक्तिगत वर्ष', 'व्यक्तिगत महीना', 'व्यक्तिगत दिन', 'आज की सार्वभौमिक संख्या']}
# Original reflections. Deliberately not guaranteed forecasts or copied horoscopes.
THEMES = {'en': ['Choose one small task and start it. Pause before making a rushed decision.', 'Listen carefully and ask for help when needed. Give yourself room to rest.', 'Express one idea clearly. A short note or an honest conversation is enough.', 'Keep the plan simple. Finish one practical task before adding another.', 'Try a small change in your routine. Keep your spending and commitments deliberate.', 'Check in with someone you care about. Help without taking on more than you can manage.', 'Make space for learning or quiet reflection. Check facts before drawing conclusions.', 'Review a practical goal and take one measured step. A number does not guarantee money or success.', 'Close one unfinished task. Let go of pressure to fix everything today.'], 'bn': ['একটা ছোট কাজ শুরু করুন। সিদ্ধান্ত নেওয়ার আগে একটু থামুন।', 'কারও কথা মন দিয়ে শুনুন। দরকার হলে সাহায্য চান।', 'মনের একটা কথা সহজ করে বলুন।', 'আগে একটা কাজ শেষ করুন। তারপর পরেরটা ধরুন।', 'ছোট একটা বদল করে দেখুন। সব একসঙ্গে বদলাবেন না।', 'কাছের কারও খোঁজ নিন। নিজের বিশ্রামও মনে রাখুন।', 'একটা জিনিস শিখুন। আগে দেখে নিন কথাটা ঠিক কি না।', 'কথা দেওয়ার আগে সময় আর খরচ দেখে নিন।', 'ঝুলে থাকা একটা কাজ শেষ করুন বা ভেবে বাদ দিন।'], 'hi': ['एक छोटा काम चुनकर शुरू करें। जल्दबाजी में फैसला करने से पहले थोड़ा रुकें।', 'ध्यान से सुनें और जरूरत पर मदद मांगें। आराम के लिए भी समय रखें।', 'एक विचार साफ शब्दों में कहें। छोटा नोट या खुलकर बात करना काफी है।', 'योजना सरल रखें। नया काम जोड़ने से पहले एक जरूरी काम पूरा करें।', 'दिनचर्या में छोटा बदलाव आजमा सकते हैं। खर्च और वादे सोचकर तय करें।', 'किसी अपने का हाल पूछें। मदद करें, लेकिन अपनी क्षमता से ज्यादा जिम्मेदारी न लें।', 'सीखने या शांति से सोचने के लिए समय रखें। निष्कर्ष से पहले तथ्य जांचें।', 'एक व्यावहारिक लक्ष्य देखें और छोटा कदम लें। कोई संख्या धन या सफलता की गारंटी नहीं है।', 'एक अधूरा काम पूरा करें। आज ही सब ठीक करने का दबाव छोड़ दें।']}
DISCLAIMER = {'en': 'Reflection, not a prediction. Not medical, financial or legal advice. Birth time/place are stored for a future natal module; no Lagna, Moon rashi or dasha is calculated in this version.', 'bn': 'এটা সংখ্যা দেখে ভাবার কিছু কথা, ভবিষ্যতের খবর নয়; টাকা, চিকিৎসা বা আইনের সিদ্ধান্ত এর ভরসায় নেবেন না। জন্মছকের কাজ পরে যোগ হবে।', 'hi': 'चिंतन के लिए, भविष्यवाणी नहीं। चिकित्सा, वित्तीय या कानूनी सलाह नहीं। जन्म का समय और स्थान भविष्य के जन्म-कुंडली मॉड्यूल के लिए रखे जाते हैं; इस संस्करण में लग्न, चंद्र राशि या दशा नहीं निकाली जाती।'}
UNAVAILABLE = {'en': 'Panchang unavailable. The number calculation still works.', 'bn': 'আজ পঞ্চাঙ্গের তথ্য আসেনি। আপনার সংখ্যার হিসাব ঠিক আছে।', 'hi': 'पंचांग अभी उपलब्ध नहीं है। संख्या की गणना फिर भी काम कर रही है।'}
INDIA_ONLY = {'en': 'Panchang in v1 is for confirmed Indian locations only. All provider times below are IST.', 'bn': 'এখন পঞ্চাঙ্গ শুধু ভারতের জায়গার জন্য। নিচের সময়গুলো ভারতের সময়।', 'hi': 'इस संस्करण में पंचांग केवल पुष्टि किए गए भारतीय स्थानों के लिए है। नीचे सभी समय IST हैं।'}

def reduce_number(value):
    n = int(value)
    if n < 1:
        raise ValueError('positive number required')
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n

def trace(value):
    n = int(value)
    steps = [str(n)]
    while n > 9:
        digits = [int(c) for c in str(n)]
        n = sum(digits)
        steps.append('+'.join(map(str,digits))+'='+str(n))
    return ' -> '.join(steps)

def numbers(dob, target):
    birth = dt.date.fromisoformat(dob)
    day = dt.date.fromisoformat(target)
    full_sum = sum(int(c) for c in dob if c.isdigit())
    year_sum = birth.day + birth.month + day.year
    py = reduce_number(year_sum)
    pm = reduce_number(py + day.month)
    sums = [birth.day, full_sum, year_sum, py+day.month, pm+day.day,
            sum(int(c) for c in target if c.isdigit())]
    return {'values':[reduce_number(n) for n in sums], 'traces':[trace(n) for n in sums], 'method':METHOD}

def request(url, method='GET', body=None, headers=None):
    data = None if body is None else json.dumps(body,ensure_ascii=False).encode()
    h = {'Content-Type':'application/json', **(headers or {})}
    req = urllib.request.Request(url,data=data,headers=h,method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        return json.loads(raw) if raw else None

def db(path, method='GET', body=None, prefer=None):
    url = os.environ['SUPABASE_URL'].rstrip('/')+'/rest/v1/'+path
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ['SB_SERVICE_ROLE_KEY']
    headers = {'apikey':key,'Authorization':'Bearer '+key}
    if prefer: headers['Prefer'] = prefer
    return request(url,method,body,headers)

def panchang(profile, date):
    if not profile['panchang_india']:
        return None
    lat,lon=profile['latitude'],profile['longitude']
    cache_key = f'kundlidost-v1:{date}:{lat}:{lon}'
    path = 'astro_cache?cache_key=eq.'+urllib.parse.quote(cache_key,safe='')
    cached=db(path)
    if cached: return cached[0]['payload']
    base=(os.environ.get('PANCHANG_BASE_URL') or 'https://kundlidost-api-833851802975.asia-south1.run.app').rstrip('/')
    data=request(base+'/api/panchang/public?'+urllib.parse.urlencode({'lat':lat,'lng':lon,'date':date}))
    if data.get('date') != date or not all(k in data for k in ('tithiNumber','nakshatra','sunrise','sunset')):
        raise ValueError('provider schema/date mismatch')
    db('astro_cache?on_conflict=cache_key','POST',{'cache_key':cache_key,'payload':data},'resolution=merge-duplicates,return=minimal')
    return data


READING = {'en': {'heads': ['Your reading', "Today's move", 'How to do it', 'What to finish', 'This month / year', 'The tension to watch', 'One rule for today'], 'opening': 'Your combination: birth {m}, path {b}, day {d}, month {mo}, year {y}. Read this as a practical prompt, not a claim about what will happen.', 'style': ['Work independently first: write your own answer before asking three people what they think.', 'Use a second pair of eyes: ask one clear question rather than waiting for someone to guess what you need.', 'Turn the idea into a visible draft: a 100-word note, a rough sketch or a 60-second explanation. Keep it to one idea.', 'Use a checklist of three steps. Tick off the first step before reorganising the whole plan.', 'Try one alternative, not five. Give the experiment a stopping point so curiosity does not scatter the day.', 'Offer one specific piece of help, with a limit on your time. Caring does not require taking over the whole problem.', 'Check one source yourself. Write what you know, what you do not know, and the next question.', 'Set a measurable finish line: one completed task, a clear amount or a written agreement. Avoid vague progress.', 'Choose what can be closed. If something no longer serves the plan, remove it instead of carrying it out of guilt.'], 'day': ['Before opening a feed, start the task you have been postponing. Give it 20 minutes and produce a first version.', 'Send one calm follow-up or ask for one clarification. Keep it to two sentences and do not chase an immediate reply.', 'Share one useful idea with one person. Make the message understandable without a long explanation.', 'Choose one unfinished practical task. Work for 25 minutes with notifications off, then check what is actually finished.', 'Change one small part of a stuck process. Test it for 15 minutes before making a bigger commitment.', 'Have one undistracted conversation with someone close. Ask what would help; do not assume you have to fix everything.', 'Read or practise one difficult thing for 20 minutes. End by writing the one point you understand better.', 'Review one commitment involving time or money. Check the actual terms before agreeing, buying or promising.', 'Finish, file or consciously drop one lingering task. Leave one less open loop at the end of the day.'], 'finish': ['Finish with a decision you can state in one sentence.', 'Finish with one clear next step agreed between the people involved.', 'Finish with something another person can read, hear or see, not just an idea in your head.', 'Finish with a repeatable checklist or a tidier working system.', 'Finish with one lesson from the experiment, even if you choose not to continue it.', 'Finish by checking that your own needs have not disappeared behind helping someone else.', 'Finish with one verified fact and one question to investigate next.', 'Finish by recording the result, cost or deadline instead of relying on memory.', 'Finish by deciding what you will not carry into tomorrow.'], 'cycles': ['begin one manageable thing', 'build cooperation without rushing a response', 'express or share work clearly', 'strengthen a simple routine', 'test a limited change', 'balance care with boundaries', 'study before expanding', 'review resources and commitments', 'complete or release unfinished work'], 'cycleLine': 'Use month {mo} to {month}; keep year {y} as the longer prompt to {year}. This does not make today a lucky or unlucky day.', 'repeat': 'Day {d} repeats your {which} number. Use that repeated theme in the single task above; do not turn repetition into a promise of luck.', 'contrast': "Your birth-number prompt is about {birth}; today's prompt is about {day}. If those pull in different directions, do the small daily task first and use your birth-number style to carry it out.", 'keys': ['starting', 'listening', 'expression', 'structure', 'experimentation', 'care', 'research', 'accountability', 'closure'], 'which': ['birth', 'path', 'birth and path'], 'rule': 'Do one thing, leave evidence that you did it, and stop treating the reading as a test you must pass.', 'birth3Day': ['Write the first 100 words of the task you keep postponing. Do not edit them until the 20-minute timer ends.', 'Send a two-sentence message: one line of context, one clear question. Leave room for the other person to answer.', 'Record a 60-second explanation of one idea. Listen once and cut the one sentence that adds no useful point.', 'Choose one unfinished draft. Give it a title, three bullet points and a next step, then stop opening new drafts.', 'Tell the same idea in two different ways: a short note and a one-minute voice draft. Compare which is clearer before sharing.', 'Tell someone close one specific thing you appreciate about them, then ask one real question about their day. Keep the phone aside while listening.', 'Read one source for 20 minutes, then explain its main idea in five lines without copying it. Mark the part you still cannot explain.', 'Before making a promise, write exactly what you will deliver and by when. Check that your words do not commit you to more than you can do.', 'Choose one unsent draft. Send it if it is ready, archive it if it is no longer needed, or write the single missing point.']}, 'bn': {'heads': ['আজ কী করতে পারেন', 'আজ একটা কাজ', 'কাজটা করবেন কীভাবে', 'শেষে কী রাখবেন', 'মাস আর বছরের কথা', 'দুটো কথা আলাদা হলে', 'মনে রাখুন'], 'opening': 'আপনার মূলাঙ্ক {m}, ভাগ্যাঙ্ক {b}। আজ আপনার সংখ্যা {d}, এ মাসের {mo}, এ বছরের {y}। এগুলো মিলিয়ে কিছু কাজের কথা বলছি। দিন ঠিক এমনই যাবে, তা বলছি না।', 'style': ['আগে নিজের ভাবনাটা লিখুন। তারপর চাইলে কারও মত নিন।', 'কী সাহায্য চান, একজনকে পরিষ্কার করে বলুন। তাঁকে আন্দাজ করতে দেবেন না।', 'একটা কথা নিয়ে ছোট করে লিখুন বা এক মিনিটে বলে দেখুন। একসঙ্গে অনেক কথা নয়।', 'তিনটে ছোট ধাপ লিখুন। প্রথমটা শেষ করে দ্বিতীয়টা ধরুন।', 'একটা নতুন উপায় করে দেখুন। কতক্ষণ দেখবেন, আগে ঠিক করুন।', 'একটু সাহায্য করুন। কিন্তু সব দায় নিজের ওপর নেবেন না।', 'একটা তথ্য নিজে দেখে নিন। যেটা বুঝলেন না, সেটা লিখে রাখুন।', 'কাজটা কখন শেষ হবে, আগে ঠিক করুন। শুধু ব্যস্ত থাকলেই কাজ হয় না।', 'যেটা আর দরকার নেই, ভেবে বাদ দিন। সব কাজ ধরে রাখতে হবে না।'], 'day': ['ফোনে অন্য কিছু দেখার আগে একটা ফেলে রাখা কাজ ধরুন। ২০ মিনিট করুন। একটু শুরু হলেই আজ লাভ।', 'একজনকে ছোট করে একটা প্রশ্ন বা খোঁজের মেসেজ দিন। সঙ্গে সঙ্গে উত্তর না এলে বারবার পাঠাবেন না।', 'একটা ভালো ভাবনা একজনকে সহজ করে বলুন। যেন শুনেই বুঝতে পারেন।', 'একটা অসমাপ্ত কাজ ধরুন। ফোন সরিয়ে ২৫ মিনিট করুন। কতটা হল দেখে নিন।', 'আটকে থাকা কাজের একটা ছোট অংশ অন্যভাবে করুন। ১৫ মিনিট দেখে নিন এতে সুবিধা হচ্ছে কি না।', 'কাছের একজনের সঙ্গে মন দিয়ে কথা বলুন। কী দরকার জিজ্ঞেস করুন। সব সমস্যা আপনাকেই মেটাতে হবে না।', 'একটা কঠিন জিনিস ২০ মিনিট পড়ুন বা করে দেখুন। শেষে কী শিখলেন, এক লাইন লিখুন।', 'টাকা বা সময় লাগবে এমন একটা কথা দেওয়ার আগে দেখে নিন। কত লাগবে, কী করতে হবে, বুঝে তবেই রাজি হন।', 'ঝুলে থাকা একটা কাজ শেষ করুন। না হলে ঠিক করুন, কবে করবেন বা আর করবেন কি না।'], 'finish': ['শেষে এক লাইনে বলুন, কী ঠিক করলেন।', 'শেষে ঠিক করুন, কে পরের কাজটা করবে আর কী করবে।', 'শেষে ছোট একটা লেখা, কথা বা ছবি রাখুন। শুধু ভাবলে হবে না।', 'শেষে ছোট একটা তালিকা রাখুন। পরেরবার কাজটা সহজ হবে।', 'শেষে কী শিখলেন লিখুন। নতুন উপায়টা না চললেও শেখাটা কাজে লাগবে।', 'শেষে দেখুন, অন্যের জন্য করতে গিয়ে নিজের দরকার ভুলে গেলেন কি না।', 'শেষে একটা ঠিক তথ্য আর একটা বাকি প্রশ্ন লিখুন।', 'কত খরচ হল বা কবে কাজ দিতে হবে, লিখে রাখুন। মনে রাখার ওপর ছাড়বেন না।', 'শেষে ঠিক করুন, কোন পুরনো কাজটা আর বয়ে বেড়াবেন না।'], 'cycles': ['ছোট একটা কাজ শুরু করুন', 'মানুষের সঙ্গে কথা বলে এগোন', 'নিজের কথা সহজ করে বলুন', 'ছোট একটা রুটিন ধরে রাখুন', 'ছোট বদল করে দেখুন', 'অন্যের খোঁজ নিন, নিজেরও যত্ন নিন', 'আগে শিখুন, তারপর বড় কাজ ধরুন', 'সময় আর টাকার হিসাব দেখুন', 'পুরনো কাজ শেষ করুন বা ভেবে বাদ দিন'], 'cycleLine': 'এ মাসের {mo} দেখে ভাবার কথা: {month}। এ বছরের {y} দেখে ভাবার কথা: {year}। এসব মানে দিন ভালো বা খারাপ হবেই, তা নয়।', 'repeat': 'আজকের {d} আপনার {which}-এর সঙ্গে মিলেছে। ওপরের ছোট কাজটায় এই মিলের ভাবনাটা রাখুন। মিলেছে বলেই ভাগ্য ভালো হবে, তা নয়।', 'contrast': 'আপনার মূলাঙ্ক দেখে ভাবার কথা {birth}। আজকের সংখ্যা দেখে ভাবার কথা {day}। দুটো আলাদা হলে আগে আজকের ছোট কাজটা ধরুন। করার সময় প্রথম কথাটাও মনে রাখুন।', 'keys': ['শুরু করা', 'মন দিয়ে শোনা', 'নিজের কথা বলা', 'গুছিয়ে করা', 'নতুন উপায় দেখা', 'খোঁজ নেওয়া', 'দেখে শেখা', 'হিসাব রাখা', 'শেষ করা'], 'which': ['মূলাঙ্ক', 'ভাগ্যাঙ্ক', 'মূলাঙ্ক আর ভাগ্যাঙ্ক'], 'rule': 'একটা কাজ হলেই ভালো। সব কথা মানতেই হবে না। যেটা আপনার কাজে লাগে, সেটাই নিন।', 'birth3Day': ['ফেলে রাখা কাজটা নিয়ে ছোট করে লেখা শুরু করুন। ২০ মিনিট শুধু লিখুন, ঠিকঠাক করার চিন্তা পরে।', 'একজনকে দুই লাইনের মেসেজ দিন। এক লাইনে কথাটা বলুন, আরেক লাইনে প্রশ্ন করুন। তারপর উত্তরের জন্য সময় দিন।', 'একটা ভাবনা এক মিনিটে রেকর্ড করে বলুন। শুনে দেখুন, কোথায় কথা বেশি হয়ে গেছে। সেই অংশ ছোট করুন।', 'একটা অসমাপ্ত লেখা ধরুন। নাম দিন, তিনটে কথা লিখুন, পরের কাজটা ঠিক করুন। নতুন লেখা এখন ধরবেন না।', 'একই কথা একবার লিখে আর একবার বলে দেখুন। কোনটা সহজে বোঝা যায় দেখুন।', 'কাছের একজনের একটা ভালো কাজের কথা বলুন। তারপর জিজ্ঞেস করুন, তাঁর দিন কেমন গেল। শোনার সময় ফোনটা সরিয়ে রাখুন।', 'একটা জিনিস ২০ মিনিট পড়ুন। নিজের ভাষায় পাঁচ লাইনে বলুন কী বুঝলেন। কোথায় আটকালেন, সেটাও লিখুন।', 'কথা দেওয়ার আগে লিখুন, কী করবেন আর কবে করবেন। যতটা পারেন, তার বেশি কথা দেবেন না।', 'না-পাঠানো একটা লেখা দেখুন। তৈরি হলে পাঠান। দরকার না থাকলে সরিয়ে রাখুন। আর কিছু বাকি থাকলে শুধু সেটুকু লিখুন।']}, 'hi': {'heads': ['आपका पाठ', 'आज का छोटा कदम', 'कैसे करें', 'कहां पूरा करें', 'यह महीना / वर्ष', 'जिस खिंचाव पर ध्यान दें', 'आज का एक नियम'], 'opening': 'आपका संयोजन: मूलांक {m}, भाग्यांक {b}, दिन {d}, महीना {mo}, वर्ष {y}। इसे व्यावहारिक चिंतन समझें, क्या होगा उसका दावा नहीं।', 'style': ['पहले अपना उत्तर लिखें। शुरू में ही तीन लोगों की राय न मांगें।', 'एक व्यक्ति की मदद से जांचें। उसे अनुमान लगाने देने के बजाय एक साफ सवाल पूछें।', 'विचार का दिखने वाला मसौदा बनाएं: 100 शब्द, छोटा चित्र या एक मिनट की व्याख्या। एक ही विषय रखें।', 'तीन कदमों की सूची बनाएं। पूरी योजना बदलने से पहले पहला कदम पूरा करें।', 'पांच नहीं, एक विकल्प जांचें। कब रुकना है तय करें, ताकि उत्सुकता दिन को बिखेर न दे।', 'समय की सीमा रखकर खास मदद दें। परवाह करने का मतलब पूरी समस्या अपने ऊपर लेना नहीं है।', 'एक स्रोत खुद जांचें। क्या जानते हैं, क्या नहीं जानते और अगला सवाल क्या है, लिखें।', 'पूरा होने का माप रखें: एक खत्म काम, स्पष्ट रकम या लिखित सहमति। अस्पष्ट प्रगति नहीं।', 'चुनें कि क्या पूरा किया जा सकता है। योजना में काम नहीं आता तो अपराधबोध में उसे ढोते न रहें।'], 'day': ['फीड खोलने से पहले टाला हुआ काम शुरू करें। 20 मिनट देकर पहला मसौदा बनाएं।', 'एक शांत फॉलो-अप भेजें या एक बात स्पष्ट पूछें। दो वाक्य रखें; तुरंत जवाब का पीछा न करें।', 'एक व्यक्ति को एक उपयोगी विचार बताएं। लंबी व्याख्या के बिना संदेश समझ आना चाहिए।', 'एक अधूरा व्यावहारिक काम चुनें। नोटिफिकेशन बंद करके 25 मिनट करें, फिर देखें वास्तव में क्या पूरा हुआ।', 'अटकी हुई प्रक्रिया का छोटा हिस्सा बदलें। बड़ी प्रतिबद्धता से पहले 15 मिनट जांचें।', 'किसी अपने से ध्यान देकर बात करें। पूछें क्या मदद चाहिए; सब ठीक करने की जिम्मेदारी न लें।', 'एक कठिन विषय 20 मिनट पढ़ें या अभ्यास करें। अंत में एक बात लिखें जो बेहतर समझी।', 'समय या पैसे वाली एक प्रतिबद्धता देखें। सहमति, खरीद या वादे से पहले असली शर्तें जांचें।', 'एक अटका काम पूरा करें, व्यवस्थित रखें या सोचकर छोड़ दें। दिन के अंत में एक खुला काम कम रखें।'], 'finish': ['अंत में फैसला एक वाक्य में बता सकें।', 'अंत में शामिल लोगों के साथ अगला एक कदम साफ करें।', 'अंत में कुछ ऐसा हो जो दूसरा पढ़, सुन या देख सके; केवल मन का विचार नहीं।', 'अंत में दोबारा इस्तेमाल होने वाली सूची या व्यवस्थित काम करने का तरीका रखें।', 'प्रयोग आगे न बढ़ाएं तब भी सीखी हुई एक बात लिखकर खत्म करें।', 'अंत में देखें कि दूसरों की मदद के पीछे अपनी जरूरतें गायब तो नहीं हुईं।', 'अंत में एक जांचा हुआ तथ्य और अगला एक सवाल रखें।', 'नतीजा, खर्च या समयसीमा लिखकर खत्म करें; केवल याददाश्त पर न रहें।', 'तय करके खत्म करें कि क्या कल तक नहीं ढोना है।'], 'cycles': ['छोटा, संभलने वाला काम शुरू करें', 'जवाब का पीछा किए बिना सहयोग बनाएं', 'काम साफ कहें या साझा करें', 'सरल दिनचर्या मजबूत करें', 'सीमित बदलाव जांचें', 'परवाह के साथ अपनी सीमाएं रखें', 'बढ़ाने से पहले सीखें', 'संसाधन और वादे जांचें', 'अधूरा काम पूरा करें या छोड़ें'], 'cycleLine': 'महीने {mo} का सूत्र: {month}। वर्ष {y} का लंबा सूत्र: {year}। इससे आज का दिन शुभ या अशुभ सिद्ध नहीं होता।', 'repeat': 'दिन {d} आपके {which} से मिलता है। ऊपर के एक काम में उसी विषय को इस्तेमाल करें; दोहराव भाग्य की गारंटी नहीं।', 'contrast': 'मूलांक का सूत्र {birth}, आज का सूत्र {day} है। अलग दिशा में खींचें तो पहले आज का छोटा काम करें; उसे करने के तरीके में मूलांक का सूत्र रखें।', 'keys': ['शुरुआत', 'सुनना', 'अभिव्यक्ति', 'व्यवस्था', 'प्रयोग', 'परवाह', 'जांच', 'जवाबदेही', 'समापन'], 'which': ['मूलांक', 'भाग्यांक', 'मूलांक और भाग्यांक'], 'rule': 'एक काम करें और उसके पूरा होने का प्रमाण रखें। पाठ को पास करना जरूरी परीक्षा न बनाएं।', 'birth3Day': ['टाले हुए काम के पहले 100 शब्द लिखें। 20 मिनट का टाइमर खत्म होने तक संपादन न करें।', 'दो वाक्यों का संदेश भेजें: एक में संदर्भ, दूसरे में साफ सवाल। सामने वाले को जवाब देने की जगह दें।', 'एक विचार की एक मिनट की रिकॉर्डिंग करें। एक बार सुनकर वह वाक्य हटाएं जो कोई उपयोगी बात नहीं जोड़ता।', 'एक अधूरा मसौदा चुनें। शीर्षक, तीन बिंदु और अगला कदम लिखें; फिर नए मसौदे खोलना बंद करें।', 'एक विचार दो तरीकों से कहें: छोटा नोट और एक मिनट का आवाज मसौदा। साझा करने से पहले देखें कौन अधिक स्पष्ट है।', 'किसी अपने की एक खास बात की सराहना करें, फिर उनके दिन पर एक असली सवाल पूछें। सुनते समय फोन अलग रखें।', 'एक स्रोत 20 मिनट पढ़ें। नकल किए बिना उसकी मुख्य बात पांच पंक्तियों में समझाएं। जो हिस्सा नहीं समझा सकते उसे चिह्नित करें।', 'वादा करने से पहले लिखें कि ठीक क्या देंगे और कब। देखें कि शब्द क्षमता से ज्यादा जिम्मेदारी तो नहीं दे रहे।', 'एक न भेजा मसौदा चुनें। तैयार हो तो भेजें, जरूरत न हो तो अलग रखें, या बची हुई एक बात लिखें।']}}

def canonical_timezone(value):
    if value.lower() in ('asia/kolkata', 'asia/calcutta'):
        return 'Asia/Kolkata'
    return value

def friendly_timezone(value):
    if value.lower() in ('asia/kolkata', 'asia/calcutta'):
        return 'IST (UTC+05:30)'
    return value

def personal_reading(n, language):
    r = READING[language]
    m,b,y,mo,d,u = n['values']
    same_birth, same_path = d == m, d == b
    which = r['which'][2 if same_birth and same_path else 0 if same_birth else 1]
    tension = r['repeat'].format(d=d,which=which) if same_birth or same_path else r['contrast'].format(birth=r['keys'][m-1],day=r['keys'][d-1])
    return '\n'.join([
        r['heads'][0], r['opening'].format(m=m,b=b,y=y,mo=mo,d=d),
        '',r['heads'][1]+f' [{d}]',r['birth3Day'][d-1] if m == 3 else r['day'][d-1],
        '',r['heads'][2]+f' [{m}]',({'en':'Say the one thing you actually mean, in two clear sentences. Then listen without planning your reply.','bn':'যা বলতে চান, দুই লাইনে সহজ করে বলুন। তারপর মন দিয়ে শুনুন।','hi':'जो सच में कहना चाहते हैं, दो साफ वाक्यों में कहें। फिर अपना जवाब सोचने के बजाय सुनें।'}[language] if m == 3 and d in (2,6) else r['style'][m-1]),
        '',r['heads'][3]+f' [{b}]',r['finish'][b-1],
        '',r['heads'][4]+f' [{mo}/{y}]',r['cycleLine'].format(mo=mo,y=y,month=r['cycles'][mo-1],year=r['cycles'][y-1]),
        '',r['heads'][5],tension,
        '',r['heads'][6],r['rule']
    ])


BN_NAKSHATRA = ['অশ্বিনী', 'ভরণী', 'কৃত্তিকা', 'রোহিণী', 'মৃগশিরা', 'আর্দ্রা', 'পুনর্বসু', 'পুষ্যা', 'আশ্লেষা', 'মঘা', 'পূর্ব ফাল্গুনী', 'উত্তর ফাল্গুনী', 'হস্তা', 'চিত্রা', 'স্বাতী', 'বিশাখা', 'অনুরাধা', 'জ্যেষ্ঠা', 'মূলা', 'পূর্বাষাঢ়া', 'উত্তরাষাঢ়া', 'শ্রবণা', 'ধনিষ্ঠা', 'শতভিষা', 'পূর্ব ভাদ্রপদ', 'উত্তর ভাদ্রপদ', 'রেবতী']

def bn_digits(value):
    return str(value).translate(str.maketrans('0123456789','০১২৩৪৫৬৭৮৯'))

def bn_timezone(value):
    return 'ভারতের সময় (UTC+০৫:৩০)' if value.lower() in ('asia/kolkata','asia/calcutta') else friendly_timezone(value)

def bn_panchang(data):
    index = data.get('nakshatraIndex')
    name = BN_NAKSHATRA[index] if isinstance(index,int) and 0 <= index < 27 else data['nakshatra']
    paksha = {'shukla':'শুক্লপক্ষ','krishna':'কৃষ্ণপক্ষ'}.get(data.get('paksha'),data.get('paksha',''))
    lines = ['তিথি: '+bn_digits(data['tithiNumber'])+' ('+paksha+')','নক্ষত্র: '+str(name),
             'সূর্যোদয়: '+bn_digits(data['sunrise'])+' | সূর্যাস্ত: '+bn_digits(data['sunset'])]
    if 'rahuKaal' in data:
        r = data['rahuKaal']; lines.append('রাহুকাল: '+bn_digits(r.get('start','?'))+' - '+bn_digits(r.get('end','?')))
    return lines


# Editorial v1 colours: 1 gold, 2 white, 3 yellow, 4 blue, 5 green,
# 6 pink, 7 purple, 8 navy, 9 red. No claim of changing outcomes.
SHORT_READING = {'en': {'heading': 'A small thought for today', 'day': ['Start one small thing today. Give it 20 minutes before deciding whether it can work.', 'Ask one clear question today. Then give the other person time to answer.', 'Share one idea in a short message today. Keep the words simple.', 'Finish one half-done task today. Put the phone aside for a little while.', 'Try one small change today. See how it works before changing everything.', 'Tell someone close one thing you appreciate today. Then listen to how their day went.', 'Learn one small thing today. You do not have to understand everything at once.', 'Check the time and cost before making a promise today. Keep it within what you can manage.', 'Close one old task today, or decide to let it go. Make a little room for tomorrow.'], 'color': "Today's symbolic lucky colour: ", 'number': "Today's symbolic lucky number: ", 'colors': ['gold', 'white', 'yellow', 'blue', 'green', 'pink', 'purple', 'navy blue', 'red'], 'notice': 'A number-based reflection, not a prediction or a promise of luck.'}, 'bn': {'heading': 'আজ আপনার জন্য ছোট্ট একটা কথা', 'day': ['আজ ছোট একটা কাজ শুরু করুন। ২০ মিনিট করে দেখুন। শুরু হলেই মনটা একটু হালকা লাগতে পারে।', 'আজ একজনকে সহজ করে একটা প্রশ্ন করুন। তারপর তাঁকে উত্তর দেওয়ার সময় দিন।', 'আজ মনের একটা ভালো কথা ছোট করে বলুন। বেশি সাজিয়ে বলতে হবে না।', 'আজ আধাখানা হয়ে থাকা একটা কাজ শেষ করুন। একটু সময় ফোনটা সরিয়ে রাখুন।', 'আজ ছোট একটা বদল করে দেখুন। ভালো লাগলে পরে এগোন। সব একসঙ্গে বদলাবেন না।', 'আজ কাছের একজনের ভালো একটা কাজের কথা বলুন। তারপর মন দিয়ে শুনুন, তাঁর দিন কেমন গেল।', 'আজ ছোট একটা জিনিস শিখুন। সব একদিনে বুঝতে হবে না।', 'আজ কথা দেওয়ার আগে সময় আর খরচ দেখে নিন। যতটা পারবেন, ততটাই কথা দিন।', 'আজ পুরনো একটা কাজ শেষ করুন বা ভেবে বাদ দিন। কালকের জন্য একটু জায়গা থাকুক।'], 'color': 'আজকের শুভ রং: ', 'number': 'আজকের শুভ সংখ্যা: ', 'colors': ['সোনালি', 'সাদা', 'হলুদ', 'নীল', 'সবুজ', 'গোলাপি', 'বেগুনি', 'গাঢ় নীল', 'লাল'], 'notice': 'এগুলো সংখ্যা দেখে ভাবার কথা, দিন বা ভাগ্য এমন হবেই তার কথা নয়।'}, 'hi': {'heading': 'आज के लिए एक छोटी बात', 'day': ['आज एक छोटा काम शुरू करें। 20 मिनट करके देखें। शुरू होने से ही थोड़ा हल्का लग सकता है।', 'आज किसी से एक साफ सवाल पूछें। फिर उसे जवाब देने का समय दें।', 'आज मन की एक अच्छी बात छोटे संदेश में कहें। शब्द सरल रखें।', 'आज एक अधूरा काम पूरा करें। थोड़ी देर फोन अलग रख दें।', 'आज एक छोटा बदलाव करके देखें। अच्छा लगे तो आगे बढ़ें, सब एक साथ न बदलें।', 'आज किसी अपने की एक अच्छी बात कहें। फिर ध्यान से सुनें कि उनका दिन कैसा गया।', 'आज एक छोटी चीज सीखें। सब एक दिन में समझना जरूरी नहीं है।', 'आज वादा करने से पहले समय और खर्च देखें। जितना कर सकते हैं, उतना ही कहें।', 'आज एक पुराना काम पूरा करें या सोचकर छोड़ दें। कल के लिए थोड़ी जगह रखें।'], 'color': 'आज का प्रतीकात्मक शुभ रंग: ', 'number': 'आज की प्रतीकात्मक शुभ संख्या: ', 'colors': ['सुनहरा', 'सफेद', 'पीला', 'नीला', 'हरा', 'गुलाबी', 'बैंगनी', 'गहरा नीला', 'लाल'], 'notice': 'संख्या देखकर सोचने की बात है, दिन या भाग्य की गारंटी नहीं।'}}

def short_reading(profile,date):
    lang = profile['language']
    r = SHORT_READING[lang]
    day = numbers(profile['dob'],date)['values'][4]
    return '\n'.join([r['heading'],r['day'][day-1],r['color']+r['colors'][day-1],
                      r['number']+(bn_digits(day) if lang == 'bn' else str(day)),r['notice']])

def render(profile,date,data=None,why=False):
    if not why:
        return short_reading(profile,date)
    lang=profile['language']
    n=numbers(profile['dob'],date)
    lines=['অ্যাস্ট্রোপালস | আজ আপনার জন্য কিছু কথা | '+bn_digits(date)+' | '+bn_timezone(profile['timezone']) if lang == 'bn' else 'AstroPulse | '+date+' | '+friendly_timezone(profile['timezone'])]
    for label,value,calc in zip(LABELS[lang],n['values'],n['traces']):
        lines.append(f"{label}: {bn_digits(value) if lang == 'bn' else value}"+(f" ({bn_digits(calc.replace(' -> ', ' → ')) if lang == 'bn' else calc})" if why else ''))
    lines+=['',bn_digits(personal_reading(n,lang)) if lang == 'bn' else personal_reading(n,lang),'',DISCLAIMER[lang]]
    if why: lines+=['','হিসাবের নিয়ম: যোগ করতে করতে শেষে ১ থেকে ৯-এর মধ্যে আনি। বছরের হিসাব জানুয়ারি থেকে ডিসেম্বর ধরে।'] if lang == 'bn' else ['',METHOD,'Calendar-year cycle; all results reduced to 1-9.']
    if data:
        lines+=['',INDIA_ONLY[lang], ('পঞ্চাঙ্গ | ' if lang == 'bn' else 'Panchang | ')+profile['location_label']]
        if lang == 'bn': lines+=bn_panchang(data)
        else:
            lines += [f"Tithi: {data['tithiNumber']} ({data.get('paksha','')})",'Nakshatra: '+str(data['nakshatra']),'Sunrise: '+str(data['sunrise'])+' | Sunset: '+str(data['sunset'])]
            if 'rahuKaal' in data:
                r=data['rahuKaal']; lines.append('Rahu Kaal: '+str(r.get('start','?'))+' - '+str(r.get('end','?')))
        lines+=[('সূত্র: ' if lang == 'bn' else 'Source: ')+'https://www.kundlidost.in/api/']
    elif not why:
        lines+=['',UNAVAILABLE[lang] if profile['panchang_india'] else INDIA_ONLY[lang]]
    return '\n'.join(lines)

def due(profile,now):
    local=now.astimezone(ZoneInfo(canonical_timezone(profile['timezone'])))
    hh,mm=map(int,profile['delivery_time'].split(':'))
    # Daily catch-up until midnight, never sends yesterday's reading.
    return (local.hour,local.minute)>=(hh,mm),local.date().isoformat()

def run():
    db('rpc/astro_cleanup','POST',{})
    profiles=[]
    offset=0
    while True:
        batch=db(f'astro_profiles?active=eq.true&select=*&order=chat_id&limit=500&offset={offset}')
        profiles.extend(batch)
        if len(batch)<500: break
        offset+=500
    counts={'sent':0,'failed':0,'unknown':0,'skipped':0}
    for profile in profiles:
        is_due,date=due(profile,dt.datetime.now(dt.timezone.utc))
        if not is_due: counts['skipped']+=1; continue
        # Atomic insert is the claim; concurrent runs cannot duplicate the daily send.
        try:
            db('astro_deliveries','POST',{'chat_id':profile['chat_id'],'local_date':date,'status':'sending'},'return=minimal')
        except urllib.error.HTTPError as e:
            if e.code==409: counts['skipped']+=1; continue
            raise
        delivery_filter=f"astro_deliveries?chat_id=eq.{profile['chat_id']}&local_date=eq.{date}"
        # A stop/delete arriving after the claim suppresses delivery.
        fresh=db(f"astro_profiles?chat_id=eq.{profile['chat_id']}&active=eq.true&select=*")
        if not fresh:
            db(delivery_filter,'DELETE'); counts['skipped']+=1; continue
        profile=fresh[0]
        try: data=panchang(profile,date)
        except (urllib.error.URLError,ValueError,KeyError,TimeoutError): data=None
        result=None
        try:
            result=request('https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']+'/sendMessage','POST',
                           {'chat_id':profile['chat_id'],'text':render(profile,date,data),'disable_web_page_preview':True})
            status='sent' if result.get('ok') else 'failed'
        except urllib.error.HTTPError:
            status='failed' # Deliberately no automatic resend after explicit HTTP failure.
        except (urllib.error.URLError,TimeoutError,ValueError):
            status='unknown' # Telegram may have accepted it; do not blindly retry.
        patch={'status':status}
        if status=='sent': patch['message_id']=result['result']['message_id']
        db(delivery_filter,'PATCH',patch)
        counts[status]+=1
        time.sleep(0.05) # stay below ~30 free broadcast messages/second
    print(json.dumps(counts)) # Never log tokens, chat ids or birth details.
    if counts['failed'] or counts['unknown']: raise SystemExit('Some deliveries need operator review; no automatic resend.')

if __name__=='__main__':
    try:
        run()
    except Exception:
        raise SystemExit('Digest failed. Check backend/service availability and settings; private details redacted.')
