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
LABELS = {
'en': ['Mulank','Bhagyank','Personal year','Personal month','Personal day','Universal day'],
'bn': ['মূলাঙ্ক','ভাগ্যাঙ্ক','ব্যক্তিগত বছর','ব্যক্তিগত মাস','ব্যক্তিগত দিন','আজকের সার্বজনীন সংখ্যা'],
'hi': ['मूलांक','भाग्यांक','व्यक्तिगत वर्ष','व्यक्तिगत महीना','व्यक्तिगत दिन','आज की सार्वभौमिक संख्या']}
# Original reflections. Deliberately not guaranteed forecasts or copied horoscopes.
THEMES = {
'en': [
'Choose one small task and start it. Pause before making a rushed decision.',
'Listen carefully and ask for help when needed. Give yourself room to rest.',
'Express one idea clearly. A short note or an honest conversation is enough.',
'Keep the plan simple. Finish one practical task before adding another.',
'Try a small change in your routine. Keep your spending and commitments deliberate.',
'Check in with someone you care about. Help without taking on more than you can manage.',
'Make space for learning or quiet reflection. Check facts before drawing conclusions.',
'Review a practical goal and take one measured step. A number does not guarantee money or success.',
'Close one unfinished task. Let go of pressure to fix everything today.'],
'bn': [
'একটি ছোট কাজ বেছে শুরু করুন। তাড়াহুড়ো করে সিদ্ধান্ত নেওয়ার আগে একটু থামুন।',
'মন দিয়ে শুনুন, দরকার হলে সাহায্য চান। বিশ্রামের জন্যও সময় রাখুন।',
'একটি ভাবনা স্পষ্ট করে বলুন। ছোট একটি লেখা বা খোলামেলা কথাই যথেষ্ট।',
'পরিকল্পনা সহজ রাখুন। নতুন কাজ ধরার আগে একটি দরকারি কাজ শেষ করুন।',
'রুটিনে ছোট পরিবর্তন করে দেখতে পারেন। খরচ ও প্রতিশ্রুতি ভেবে ঠিক করুন।',
'কাছের কারও খোঁজ নিন। সাহায্য করুন, তবে নিজের সামর্থ্যের বাইরে দায় নেবেন না।',
'শেখা বা শান্তভাবে ভাবার সময় রাখুন। সিদ্ধান্তের আগে তথ্য যাচাই করুন।',
'একটি বাস্তব লক্ষ্য দেখে ছোট পদক্ষেপ নিন। কোনও সংখ্যা টাকা বা সাফল্যের নিশ্চয়তা দেয় না।',
'একটি অসমাপ্ত কাজ গুছিয়ে নিন। আজই সব ঠিক করার চাপ ছেড়ে দিন।'],
'hi': [
'एक छोटा काम चुनकर शुरू करें। जल्दबाजी में फैसला करने से पहले थोड़ा रुकें।',
'ध्यान से सुनें और जरूरत पर मदद मांगें। आराम के लिए भी समय रखें।',
'एक विचार साफ शब्दों में कहें। छोटा नोट या खुलकर बात करना काफी है।',
'योजना सरल रखें। नया काम जोड़ने से पहले एक जरूरी काम पूरा करें।',
'दिनचर्या में छोटा बदलाव आजमा सकते हैं। खर्च और वादे सोचकर तय करें।',
'किसी अपने का हाल पूछें। मदद करें, लेकिन अपनी क्षमता से ज्यादा जिम्मेदारी न लें।',
'सीखने या शांति से सोचने के लिए समय रखें। निष्कर्ष से पहले तथ्य जांचें।',
'एक व्यावहारिक लक्ष्य देखें और छोटा कदम लें। कोई संख्या धन या सफलता की गारंटी नहीं है।',
'एक अधूरा काम पूरा करें। आज ही सब ठीक करने का दबाव छोड़ दें।']}
DISCLAIMER = {
'en': 'Reflection, not a prediction. Not medical, financial or legal advice. Birth time/place are stored for a future natal module; no Lagna, Moon rashi or dasha is calculated in this version.',
'bn': 'ভাবনার সহায়তা, ভবিষ্যদ্বাণী নয়। চিকিৎসা, অর্থ বা আইনি পরামর্শ নয়। জন্মের সময় ও স্থান ভবিষ্যতের জন্মছক মডিউলের জন্য রাখা হচ্ছে; এই সংস্করণে লগ্ন, চন্দ্ররাশি বা দশা গণনা হয় না।',
'hi': 'चिंतन के लिए, भविष्यवाणी नहीं। चिकित्सा, वित्तीय या कानूनी सलाह नहीं। जन्म का समय और स्थान भविष्य के जन्म-कुंडली मॉड्यूल के लिए रखे जाते हैं; इस संस्करण में लग्न, चंद्र राशि या दशा नहीं निकाली जाती।'}
UNAVAILABLE = {'en':'Panchang unavailable. The number calculation still works.', 'bn':'পঞ্চাঙ্গ এখন পাওয়া যাচ্ছে না। সংখ্যার গণনা ঠিকই কাজ করছে।', 'hi':'पंचांग अभी उपलब्ध नहीं है। संख्या की गणना फिर भी काम कर रही है।'}
INDIA_ONLY = {'en':'Panchang in v1 is for confirmed Indian locations only. All provider times below are IST.', 'bn':'এই সংস্করণে পঞ্চাঙ্গ শুধু নিশ্চিত ভারতীয় স্থানের জন্য। নিচের সব সময় IST।', 'hi':'इस संस्करण में पंचांग केवल पुष्टि किए गए भारतीय स्थानों के लिए है। नीचे सभी समय IST हैं।'}

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


READING = {'en': {'heads': ['Your reading', "Today's move", 'How to do it', 'What to finish', 'This month / year', 'The tension to watch', 'One rule for today'], 'opening': 'Your combination: birth {m}, path {b}, day {d}, month {mo}, year {y}. Read this as a practical prompt, not a claim about what will happen.', 'style': ['Work independently first: write your own answer before asking three people what they think.', 'Use a second pair of eyes: ask one clear question rather than waiting for someone to guess what you need.', 'Turn the idea into a visible draft: a 100-word note, a rough sketch or a 60-second explanation. Keep it to one idea.', 'Use a checklist of three steps. Tick off the first step before reorganising the whole plan.', 'Try one alternative, not five. Give the experiment a stopping point so curiosity does not scatter the day.', 'Offer one specific piece of help, with a limit on your time. Caring does not require taking over the whole problem.', 'Check one source yourself. Write what you know, what you do not know, and the next question.', 'Set a measurable finish line: one completed task, a clear amount or a written agreement. Avoid vague progress.', 'Choose what can be closed. If something no longer serves the plan, remove it instead of carrying it out of guilt.'], 'day': ['Before opening a feed, start the task you have been postponing. Give it 20 minutes and produce a first version.', 'Send one calm follow-up or ask for one clarification. Keep it to two sentences and do not chase an immediate reply.', 'Share one useful idea with one person. Make the message understandable without a long explanation.', 'Choose one unfinished practical task. Work for 25 minutes with notifications off, then check what is actually finished.', 'Change one small part of a stuck process. Test it for 15 minutes before making a bigger commitment.', 'Have one undistracted conversation with someone close. Ask what would help; do not assume you have to fix everything.', 'Read or practise one difficult thing for 20 minutes. End by writing the one point you understand better.', 'Review one commitment involving time or money. Check the actual terms before agreeing, buying or promising.', 'Finish, file or consciously drop one lingering task. Leave one less open loop at the end of the day.'], 'finish': ['Finish with a decision you can state in one sentence.', 'Finish with one clear next step agreed between the people involved.', 'Finish with something another person can read, hear or see, not just an idea in your head.', 'Finish with a repeatable checklist or a tidier working system.', 'Finish with one lesson from the experiment, even if you choose not to continue it.', 'Finish by checking that your own needs have not disappeared behind helping someone else.', 'Finish with one verified fact and one question to investigate next.', 'Finish by recording the result, cost or deadline instead of relying on memory.', 'Finish by deciding what you will not carry into tomorrow.'], 'cycles': ['begin one manageable thing', 'build cooperation without rushing a response', 'express or share work clearly', 'strengthen a simple routine', 'test a limited change', 'balance care with boundaries', 'study before expanding', 'review resources and commitments', 'complete or release unfinished work'], 'cycleLine': 'Use month {mo} to {month}; keep year {y} as the longer prompt to {year}. This does not make today a lucky or unlucky day.', 'repeat': 'Day {d} repeats your {which} number. Use that repeated theme in the single task above; do not turn repetition into a promise of luck.', 'contrast': "Your birth-number prompt is about {birth}; today's prompt is about {day}. If those pull in different directions, do the small daily task first and use your birth-number style to carry it out.", 'keys': ['starting', 'listening', 'expression', 'structure', 'experimentation', 'care', 'research', 'accountability', 'closure'], 'which': ['birth', 'path', 'birth and path'], 'rule': 'Do one thing, leave evidence that you did it, and stop treating the reading as a test you must pass.', 'birth3Day': ['Write the first 100 words of the task you keep postponing. Do not edit them until the 20-minute timer ends.', 'Send a two-sentence message: one line of context, one clear question. Leave room for the other person to answer.', 'Record a 60-second explanation of one idea. Listen once and cut the one sentence that adds no useful point.', 'Choose one unfinished draft. Give it a title, three bullet points and a next step, then stop opening new drafts.', 'Tell the same idea in two different ways: a short note and a one-minute voice draft. Compare which is clearer before sharing.', 'Tell someone close one specific thing you appreciate about them, then ask one real question about their day. Keep the phone aside while listening.', 'Read one source for 20 minutes, then explain its main idea in five lines without copying it. Mark the part you still cannot explain.', 'Before making a promise, write exactly what you will deliver and by when. Check that your words do not commit you to more than you can do.', 'Choose one unsent draft. Send it if it is ready, archive it if it is no longer needed, or write the single missing point.']}, 'bn': {'heads': ['আপনার পাঠ', 'আজকের ছোট কাজ', 'কীভাবে করবেন', 'কোথায় শেষ করবেন', 'এই মাস / বছর', 'যে টানটা খেয়াল করবেন', 'আজকের একটি নিয়ম'], 'opening': 'আপনার সমন্বয়: মূলাঙ্ক {m}, ভাগ্যাঙ্ক {b}, দিন {d}, মাস {mo}, বছর {y}। এটি ব্যবহারিক ভাবনার সূত্র, কী ঘটবে তার দাবি নয়।', 'style': ['আগে নিজের উত্তর লিখুন। শুরুতেই তিনজনের মতামত চাইতে যাবেন না।', 'একজনের সাহায্যে যাচাই করুন। আপনার কী দরকার, আন্দাজের অপেক্ষা না করে একটি স্পষ্ট প্রশ্ন করুন।', 'ভাবনাটি দৃশ্যমান খসড়া করুন: ১০০ শব্দের লেখা, ছোট স্কেচ বা এক মিনিটের ব্যাখ্যা। একটি বিষয়েই থাকুন।', 'তিন ধাপের তালিকা করুন। পুরো পরিকল্পনা বদলানোর আগে প্রথম ধাপটি শেষ করুন।', 'পাঁচটি নয়, একটি বিকল্প পরীক্ষা করুন। কখন থামবেন ঠিক রাখুন, যাতে কৌতূহলে দিন ছড়িয়ে না যায়।', 'সময়ের সীমা রেখে নির্দিষ্ট সাহায্য করুন। যত্ন মানে পুরো সমস্যার দায় নেওয়া নয়।', 'একটি সূত্র নিজে যাচাই করুন। কী জানেন, কী জানেন না, আর পরের প্রশ্ন কী - লিখুন।', 'শেষের মাপকাঠি রাখুন: একটি শেষ কাজ, স্পষ্ট অঙ্ক বা লিখিত সম্মতি। অস্পষ্ট অগ্রগতি নয়।', 'কী গুছিয়ে শেষ করা যায় বাছুন। পরিকল্পনায় আর কাজে না লাগলে অপরাধবোধে সেটি বয়ে বেড়াবেন না।'], 'day': ['ফিড খোলার আগে পিছিয়ে রাখা কাজটি ধরুন। ২০ মিনিট দিয়ে প্রথম খসড়া তৈরি করুন।', 'একটি শান্ত ফলো-আপ পাঠান বা একটি বিষয় পরিষ্কার করে জিজ্ঞেস করুন। দুই বাক্যে রাখুন; সঙ্গে সঙ্গে উত্তর তাড়া করবেন না।', 'একজনকে একটি দরকারি ভাবনা বলুন। লম্বা ব্যাখ্যা ছাড়াই যেন মেসেজটি বোঝা যায়।', 'একটি অসমাপ্ত বাস্তব কাজ বেছে নিন। নোটিফিকেশন বন্ধ করে ২৫ মিনিট করুন, তারপর সত্যিই কতটা শেষ হল দেখুন।', 'আটকে থাকা পদ্ধতির একটি ছোট অংশ বদলান। বড় প্রতিশ্রুতির আগে ১৫ মিনিট পরীক্ষা করুন।', 'কাছের একজনের সঙ্গে মন দিয়ে কথা বলুন। কী সাহায্য দরকার জিজ্ঞেস করুন; সব ঠিক করার দায় নেবেন না।', 'একটি কঠিন বিষয় ২০ মিনিট পড়ুন বা অভ্যাস করুন। শেষে কোন একটি জিনিস আরও ভালো বুঝলেন লিখুন।', 'সময় বা টাকা জড়িত একটি প্রতিশ্রুতি দেখুন। রাজি হওয়া, কেনা বা কথা দেওয়ার আগে আসল শর্ত যাচাই করুন।', 'একটি ঝুলে থাকা কাজ শেষ করুন, গুছিয়ে রাখুন বা ভেবে বাদ দিন। দিনের শেষে একটি খোলা কাজ কম রাখুন।'], 'finish': ['শেষে সিদ্ধান্তটি এক বাক্যে বলতে পারুন।', 'শেষে সংশ্লিষ্ট মানুষের সঙ্গে পরের একটি ধাপ স্পষ্ট করুন।', 'শেষে এমন কিছু রাখুন যা অন্য কেউ পড়তে, শুনতে বা দেখতে পারে; শুধু মাথার ভাবনা নয়।', 'শেষে আবার ব্যবহার করা যায় এমন তালিকা বা গুছানো কাজের ব্যবস্থা রাখুন।', 'পরীক্ষা চালিয়ে না গেলেও কী শিখলেন, একটি কথা লিখে শেষ করুন।', 'শেষে দেখুন, অন্যের সাহায্যের আড়ালে নিজের দরকার হারিয়ে গেল কি না।', 'শেষে একটি যাচাই করা তথ্য আর পরের একটি প্রশ্ন রাখুন।', 'ফল, খরচ বা সময়সীমা লিখে শেষ করুন; শুধু মনে রাখার ভরসায় নয়।', 'আগামীকাল কোন জিনিস আর বয়ে নেবেন না, ঠিক করে শেষ করুন।'], 'cycles': ['ছোট ও সামলানো যায় এমন কিছু শুরু করুন', 'উত্তর তাড়া না করে সহযোগিতা গড়ুন', 'কাজ স্পষ্ট করে বলুন বা ভাগ করুন', 'সহজ রুটিন মজবুত করুন', 'সীমা রেখে পরিবর্তন পরীক্ষা করুন', 'যত্নের সঙ্গে নিজের সীমাও রাখুন', 'বাড়ানোর আগে শিখুন', 'সময়, টাকা ও প্রতিশ্রুতি যাচাই করুন', 'অসমাপ্ত কাজ শেষ করুন বা ছেড়ে দিন'], 'cycleLine': 'মাস {mo}-এর সূত্র: {month}। বছরের {y}-এর দীর্ঘ সূত্র: {year}। এতে আজকের দিন শুভ বা অশুভ প্রমাণ হয় না।', 'repeat': 'আজকের {d} আপনার {which}-এর সঙ্গে মিলে যাচ্ছে। ওপরের একটি কাজেই সেই ভাবনাটি ব্যবহার করুন; মিল মানে ভাগ্যের নিশ্চয়তা নয়।', 'contrast': 'মূলাঙ্কের সূত্র {birth}, আজকের সূত্র {day}। দুটো আলাদা দিকে টানলে আগে আজকের ছোট কাজটি করুন; করার ধরনে মূলাঙ্কের সূত্র ব্যবহার করুন।', 'keys': ['শুরু করা', 'শোনা', 'প্রকাশ করা', 'গুছিয়ে করা', 'পরীক্ষা করা', 'যত্ন নেওয়া', 'যাচাই করা', 'হিসাব রাখা', 'শেষ করা'], 'which': ['মূলাঙ্ক', 'ভাগ্যাঙ্ক', 'মূলাঙ্ক ও ভাগ্যাঙ্ক'], 'rule': 'একটি কাজ করুন, করার প্রমাণ রাখুন। পাঠটিকে পাশ করতেই হবে এমন পরীক্ষা বানাবেন না।', 'birth3Day': ['পিছিয়ে রাখা কাজটির প্রথম ১০০ শব্দ লিখুন। ২০ মিনিটের টাইমার শেষ না হওয়া পর্যন্ত সম্পাদনা করবেন না।', 'দুই বাক্যের মেসেজ পাঠান: এক লাইনে প্রসঙ্গ, অন্য লাইনে স্পষ্ট প্রশ্ন। অপরজনকে উত্তর দেওয়ার জায়গা দিন।', 'একটি ভাবনা এক মিনিটে রেকর্ড করে বলুন। একবার শুনে যে বাক্যে দরকারি কিছু যোগ হয়নি সেটি বাদ দিন।', 'একটি অসমাপ্ত খসড়া বাছুন। শিরোনাম, তিনটি পয়েন্ট ও পরের ধাপ লিখুন; তারপর নতুন খসড়া খোলা থামান।', 'একই ভাবনা দুইভাবে বলুন: ছোট লেখা আর এক মিনিটের ভয়েস খসড়া। পাঠানোর আগে কোনটা বেশি স্পষ্ট দেখুন।', 'কাছের কাউকে তাঁর একটি নির্দিষ্ট কাজের প্রশংসা করুন, তারপর তাঁর দিন নিয়ে একটি সত্যিকারের প্রশ্ন করুন। শোনার সময় ফোন সরিয়ে রাখুন।', 'একটি সূত্র ২০ মিনিট পড়ুন। নকল না করে মূল কথাটি পাঁচ লাইনে বুঝিয়ে লিখুন। যে অংশ বোঝাতে পারছেন না চিহ্নিত করুন।', 'কথা দেওয়ার আগে লিখুন ঠিক কী করবেন ও কবে দেবেন। আপনার কথায় সামর্থ্যের বেশি দায় চলে আসছে কি না দেখুন।', 'না-পাঠানো একটি খসড়া বাছুন। প্রস্তুত হলে পাঠান, আর দরকার না হলে গুছিয়ে সরান, অথবা যে একটি কথা বাকি সেটি লিখুন।']}, 'hi': {'heads': ['आपका पाठ', 'आज का छोटा कदम', 'कैसे करें', 'कहां पूरा करें', 'यह महीना / वर्ष', 'जिस खिंचाव पर ध्यान दें', 'आज का एक नियम'], 'opening': 'आपका संयोजन: मूलांक {m}, भाग्यांक {b}, दिन {d}, महीना {mo}, वर्ष {y}। इसे व्यावहारिक चिंतन समझें, क्या होगा उसका दावा नहीं।', 'style': ['पहले अपना उत्तर लिखें। शुरू में ही तीन लोगों की राय न मांगें।', 'एक व्यक्ति की मदद से जांचें। उसे अनुमान लगाने देने के बजाय एक साफ सवाल पूछें।', 'विचार का दिखने वाला मसौदा बनाएं: 100 शब्द, छोटा चित्र या एक मिनट की व्याख्या। एक ही विषय रखें।', 'तीन कदमों की सूची बनाएं। पूरी योजना बदलने से पहले पहला कदम पूरा करें।', 'पांच नहीं, एक विकल्प जांचें। कब रुकना है तय करें, ताकि उत्सुकता दिन को बिखेर न दे।', 'समय की सीमा रखकर खास मदद दें। परवाह करने का मतलब पूरी समस्या अपने ऊपर लेना नहीं है।', 'एक स्रोत खुद जांचें। क्या जानते हैं, क्या नहीं जानते और अगला सवाल क्या है, लिखें।', 'पूरा होने का माप रखें: एक खत्म काम, स्पष्ट रकम या लिखित सहमति। अस्पष्ट प्रगति नहीं।', 'चुनें कि क्या पूरा किया जा सकता है। योजना में काम नहीं आता तो अपराधबोध में उसे ढोते न रहें।'], 'day': ['फीड खोलने से पहले टाला हुआ काम शुरू करें। 20 मिनट देकर पहला मसौदा बनाएं।', 'एक शांत फॉलो-अप भेजें या एक बात स्पष्ट पूछें। दो वाक्य रखें; तुरंत जवाब का पीछा न करें।', 'एक व्यक्ति को एक उपयोगी विचार बताएं। लंबी व्याख्या के बिना संदेश समझ आना चाहिए।', 'एक अधूरा व्यावहारिक काम चुनें। नोटिफिकेशन बंद करके 25 मिनट करें, फिर देखें वास्तव में क्या पूरा हुआ।', 'अटकी हुई प्रक्रिया का छोटा हिस्सा बदलें। बड़ी प्रतिबद्धता से पहले 15 मिनट जांचें।', 'किसी अपने से ध्यान देकर बात करें। पूछें क्या मदद चाहिए; सब ठीक करने की जिम्मेदारी न लें।', 'एक कठिन विषय 20 मिनट पढ़ें या अभ्यास करें। अंत में एक बात लिखें जो बेहतर समझी।', 'समय या पैसे वाली एक प्रतिबद्धता देखें। सहमति, खरीद या वादे से पहले असली शर्तें जांचें।', 'एक अटका काम पूरा करें, व्यवस्थित रखें या सोचकर छोड़ दें। दिन के अंत में एक खुला काम कम रखें।'], 'finish': ['अंत में फैसला एक वाक्य में बता सकें।', 'अंत में शामिल लोगों के साथ अगला एक कदम साफ करें।', 'अंत में कुछ ऐसा हो जो दूसरा पढ़, सुन या देख सके; केवल मन का विचार नहीं।', 'अंत में दोबारा इस्तेमाल होने वाली सूची या व्यवस्थित काम करने का तरीका रखें।', 'प्रयोग आगे न बढ़ाएं तब भी सीखी हुई एक बात लिखकर खत्म करें।', 'अंत में देखें कि दूसरों की मदद के पीछे अपनी जरूरतें गायब तो नहीं हुईं।', 'अंत में एक जांचा हुआ तथ्य और अगला एक सवाल रखें।', 'नतीजा, खर्च या समयसीमा लिखकर खत्म करें; केवल याददाश्त पर न रहें।', 'तय करके खत्म करें कि क्या कल तक नहीं ढोना है।'], 'cycles': ['छोटा, संभलने वाला काम शुरू करें', 'जवाब का पीछा किए बिना सहयोग बनाएं', 'काम साफ कहें या साझा करें', 'सरल दिनचर्या मजबूत करें', 'सीमित बदलाव जांचें', 'परवाह के साथ अपनी सीमाएं रखें', 'बढ़ाने से पहले सीखें', 'संसाधन और वादे जांचें', 'अधूरा काम पूरा करें या छोड़ें'], 'cycleLine': 'महीने {mo} का सूत्र: {month}। वर्ष {y} का लंबा सूत्र: {year}। इससे आज का दिन शुभ या अशुभ सिद्ध नहीं होता।', 'repeat': 'दिन {d} आपके {which} से मिलता है। ऊपर के एक काम में उसी विषय को इस्तेमाल करें; दोहराव भाग्य की गारंटी नहीं।', 'contrast': 'मूलांक का सूत्र {birth}, आज का सूत्र {day} है। अलग दिशा में खींचें तो पहले आज का छोटा काम करें; उसे करने के तरीके में मूलांक का सूत्र रखें।', 'keys': ['शुरुआत', 'सुनना', 'अभिव्यक्ति', 'व्यवस्था', 'प्रयोग', 'परवाह', 'जांच', 'जवाबदेही', 'समापन'], 'which': ['मूलांक', 'भाग्यांक', 'मूलांक और भाग्यांक'], 'rule': 'एक काम करें और उसके पूरा होने का प्रमाण रखें। पाठ को पास करना जरूरी परीक्षा न बनाएं।', 'birth3Day': ['टाले हुए काम के पहले 100 शब्द लिखें। 20 मिनट का टाइमर खत्म होने तक संपादन न करें।', 'दो वाक्यों का संदेश भेजें: एक में संदर्भ, दूसरे में साफ सवाल। सामने वाले को जवाब देने की जगह दें।', 'एक विचार की एक मिनट की रिकॉर्डिंग करें। एक बार सुनकर वह वाक्य हटाएं जो कोई उपयोगी बात नहीं जोड़ता।', 'एक अधूरा मसौदा चुनें। शीर्षक, तीन बिंदु और अगला कदम लिखें; फिर नए मसौदे खोलना बंद करें।', 'एक विचार दो तरीकों से कहें: छोटा नोट और एक मिनट का आवाज मसौदा। साझा करने से पहले देखें कौन अधिक स्पष्ट है।', 'किसी अपने की एक खास बात की सराहना करें, फिर उनके दिन पर एक असली सवाल पूछें। सुनते समय फोन अलग रखें।', 'एक स्रोत 20 मिनट पढ़ें। नकल किए बिना उसकी मुख्य बात पांच पंक्तियों में समझाएं। जो हिस्सा नहीं समझा सकते उसे चिह्नित करें।', 'वादा करने से पहले लिखें कि ठीक क्या देंगे और कब। देखें कि शब्द क्षमता से ज्यादा जिम्मेदारी तो नहीं दे रहे।', 'एक न भेजा मसौदा चुनें। तैयार हो तो भेजें, जरूरत न हो तो अलग रखें, या बची हुई एक बात लिखें।']}}

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
        '',r['heads'][2]+f' [{m}]',({'en':'Say the one thing you actually mean, in two clear sentences. Then listen without planning your reply.','bn':'যে কথাটি সত্যিই বলতে চান, দুইটি স্পষ্ট বাক্যে বলুন। তারপর নিজের উত্তর ভাবতে না থেকে শুনুন।','hi':'जो सच में कहना चाहते हैं, दो साफ वाक्यों में कहें। फिर अपना जवाब सोचने के बजाय सुनें।'}[language] if m == 3 and d in (2,6) else r['style'][m-1]),
        '',r['heads'][3]+f' [{b}]',r['finish'][b-1],
        '',r['heads'][4]+f' [{mo}/{y}]',r['cycleLine'].format(mo=mo,y=y,month=r['cycles'][mo-1],year=r['cycles'][y-1]),
        '',r['heads'][5],tension,
        '',r['heads'][6],r['rule']
    ])

def render(profile,date,data=None,why=False):
    lang=profile['language']
    n=numbers(profile['dob'],date)
    lines=['AstroPulse | '+date+' | '+friendly_timezone(profile['timezone'])]
    for label,value,calc in zip(LABELS[lang],n['values'],n['traces']):
        lines.append(f'{label}: {value}'+(f' ({calc})' if why else ''))
    lines+=['',personal_reading(n,lang),'',DISCLAIMER[lang]]
    if why: lines+=['',METHOD,'Calendar-year cycle; all results reduced to 1-9.']
    if data:
        lines+=['',INDIA_ONLY[lang], 'Panchang | '+profile['location_label'],
                f"Tithi: {data['tithiNumber']} ({data.get('paksha','')})",
                'Nakshatra: '+str(data['nakshatra']),
                'Sunrise: '+str(data['sunrise'])+' | Sunset: '+str(data['sunset'])]
        if 'rahuKaal' in data:
            r=data['rahuKaal']; lines.append('Rahu Kaal: '+str(r.get('start','?'))+' - '+str(r.get('end','?')))
        lines+=['Source: https://www.kundlidost.in/api/']
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
    except Exception as e:
        print('DIGEST ERROR:', type(e).__name__, str(e)[:200]); raise SystemExit('Digest failed.')
