#!/usr/bin/env python3
# split_audio.py — 把一套完整的雅思听力录音按 Section/Part 切成 4 个分 Part 音频。
#
# 背景：剑1/2/4 全部、剑7 Test3、剑16 Test1 当初只有整套 test_X.mp3，没有分 Part。
# 本脚本用 faster-whisper（本地语音识别）转写录音，定位每个 Section/Part 的口播起点
# （剑1-14 是 "turn to section N"，剑15+ 是 "Part N. You will hear..."），按起点前
# 1.5 秒切分，输出 test_T_part_1..4.mp3 到源文件同目录。
#
# 依赖：ffmpeg、ffprobe（命令行）+ pip install faster-whisper
# 用法：python3 split_audio.py <整套mp3路径> <book编号> <test编号>
#   例: python3 split_audio.py ../ielts_listening/book_01/test_1.mp3 1 1
# 可重复调用、断点续传（每个分块转写结果缓存在本目录 _split_cache/）；
# 打印 status: partial（还没转写完，再调一次）/ done（已切好）/ error（见 error 字段）。
import sys, re, json, subprocess, time, os, hashlib

if len(sys.argv) != 4:
    print("用法: python3 split_audio.py <src.mp3> <book> <test>"); sys.exit(1)
src = sys.argv[1]; book = int(sys.argv[2]); test = int(sys.argv[3])
MARGIN = 1.5          # 切点 = 口播起点前 1.5 秒余量
WIN = 330            # 转写分块窗口长度（秒）
STEP = 300           # 分块步长（30 秒重叠，避免边界处漏词）
TIME_BUDGET = 27.0   # 单次调用转写时间预算，超过就保存进度退出
t0 = time.time()

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_split_cache")
os.makedirs(CACHE, exist_ok=True)
tag = hashlib.md5(src.encode()).hexdigest()[:10]

def probe(field, sel="format"):
    args = ["ffprobe","-v","error"]
    if sel=="stream": args += ["-select_streams","a:0"]
    args += ["-show_entries","%s=%s"%(sel,field),"-of","csv=p=0",src]
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()

def real_duration():
    # ffprobe 报的 duration 在部分老 mp3 上不准，用解码法取真实时长
    r = subprocess.run(["ffmpeg","-i",src,"-f","null","-"], capture_output=True, text=True)
    ms = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", r.stderr)
    if ms:
        h,m,s = ms[-1]
        return int(h)*3600 + int(m)*60 + float(s)
    return float(probe("duration"))

dur = real_duration()
chunk_starts = list(range(0, int(dur), STEP))

def cache_path(k): return f"{CACHE}/{tag}_c{k}.json"
done_chunks = {}
for k in chunk_starts:
    if os.path.exists(cache_path(k)):
        done_chunks[k] = json.load(open(cache_path(k)))

model = None
def get_model():
    global model
    if model is None:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=4)
    return model

for k in chunk_starts:
    if k in done_chunks: continue
    if time.time() - t0 > TIME_BUDGET: break
    tmp = f"/tmp/_ch_{tag}_{k}.mp3"
    subprocess.run(["ffmpeg","-y","-ss",str(k),"-t",str(WIN),"-i",src,
                    "-ac","1","-ar","16000","-b:a","32k",tmp], capture_output=True)
    segs,_ = get_model().transcribe(tmp, language="en", word_timestamps=True)
    words = []
    for s in segs:
        if s.words:
            for w in s.words:
                words.append([round(float(w.start)+k,2), w.word])
    json.dump(words, open(cache_path(k),"w"), ensure_ascii=False)
    done_chunks[k] = words
    try: os.remove(tmp)
    except: pass

remaining = [k for k in chunk_starts if k not in done_chunks]
if remaining:
    print(json.dumps({"status":"partial","src":src,"done":len(done_chunks),
        "total":len(chunk_starts),"remaining":remaining,
        "elapsed":round(time.time()-t0,1)}, ensure_ascii=False))
    sys.exit(0)

# 全部分块转写完成：合并 → 定位 Section/Part 边界 → 切割
allwords = []
for k in chunk_starts: allwords += done_chunks[k]
allwords.sort()
seen=set(); words=[]
for ts,w in allwords:
    key=(round(ts), re.sub(r'[^a-z0-9]','',w.lower()))
    if key in seen: continue
    seen.add(key); words.append((ts,w))

nummap={'1':1,'one':1,'won':1,'2':2,'two':2,'too':2,'3':3,'three':3,'4':4,'four':4,'for':4,'fore':4}
def clean(w): return re.sub(r'[^a-z]','',w.lower())
def tonum(w): return nummap.get(re.sub(r'[^a-z0-9]','',w.lower()))
def cleanw(j): return clean(words[j][1]) if 0<=j<len(words) else ''

cues={}
for i in range(len(words)):
    wl=clean(words[i][1])
    if wl not in ('section','part') or i+1>=len(words): continue
    n=tonum(words[i+1][1])
    if not n: continue
    if wl=='section':                          # 旧格式: "(now) turn to section N"
        if i<1: continue
        if clean(words[i-1][1]) not in ('to','turn','time','turning','now'): continue
        ctx=' '.join(cleanw(j) for j in range(max(0,i-5),i))
        if not ('turn' in ctx or 'time' in ctx or 'turning' in ctx): continue
        start_idx=i-1
        for j in range(i-1,max(0,i-6)-1,-1):
            if cleanw(j) in ('now','turn','time','turning'): start_idx=j
    else:                                       # 新格式: "Part N. You will hear..."
        nxt2=[cleanw(j) for j in range(i+2,i+4)]
        nxt4=[cleanw(j) for j in range(i+2,i+6)]
        if 'you' not in nxt2: continue
        if not ('hear' in nxt4 or 'listen' in nxt4): continue
        start_idx=i
    if n not in cues: cues[n]=round(words[start_idx][0],2)

res={"status":"error","src":src,"book":book,"test":test,
     "duration":round(dur,1),"cues":cues,"elapsed":round(time.time()-t0,1)}
if not all(k in cues for k in (2,3,4)):
    res["error"]="未找到全部 section/part 2/3/4 引导句: %s"%cues
elif not (0<cues[2]<cues[3]<cues[4]<dur):
    res["error"]="边界顺序异常: %s"%cues
else:
    b2,b3,b4=cues[2]-MARGIN,cues[3]-MARGIN,cues[4]-MARGIN
    spans=[(0,b2),(b2,b3),(b3,b4),(b4,dur)]
    if any((e-s)<90 for s,e in spans):
        res["error"]="存在过短 part（源文件可能截断）: %s"%[(round(s),round(e)) for s,e in spans]
    else:
        sr=probe("sample_rate","stream") or "44100"
        ch=probe("channels","stream") or "1"
        try: brk=max(48,min(192,int(probe("bit_rate","stream"))//1000))
        except: brk=128
        d=os.path.dirname(src); parts=[]
        for idx,(s,e) in enumerate(spans,1):
            out=f"{d}/test_{test}_part_{idx}.mp3"
            cmd=["ffmpeg","-y","-ss",f"{s:.2f}"]
            if idx<4: cmd+=["-to",f"{e:.2f}"]
            cmd+=["-i",src,"-c:a","libmp3lame","-b:a",f"{brk}k","-ar",sr,"-ac",ch,out]
            subprocess.run(cmd,capture_output=True)
            od=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                "-of","csv=p=0",out],capture_output=True,text=True).stdout.strip() or 0)
            parts.append({"part":idx,"start":round(s,2),"expected":round(e-s,1),"actual":round(od,1)})
        tot=sum(p["actual"] for p in parts)
        res["parts"]=parts
        res["sum_check"]={"parts_total":round(tot,1),"source":round(dur,1),"diff":round(tot-dur,1)}
        res["params"]={"sample_rate":sr,"channels":ch,"bitrate_k":brk}
        res["status"]="done" if abs(tot-dur)<3 else "error"
        if res["status"]!="done": res["error"]="切出的各 part 时长合计与源文件不符"
print(json.dumps(res,ensure_ascii=False,indent=1))
