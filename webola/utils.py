import subprocess

def join_nonempty(sep,*args):
    return sep.join(filter(lambda s: len(s)>0, args))

def time2str(d, zehntel=True):
    d   = d or 0
    f   = "-" if d < 0 else ""
    s,z = divmod(round(abs(10*d)), 10)
    m,s = divmod(         s , 60)
    h,m = divmod(         m , 60)
    
    s = s if zehntel else (
        s if z < 5   else (
        s+1 )) 
    
    if h == 0:
        if zehntel:
            return "%s%02d:%02d.%d"      % (f   ,m,s,z)
        else:
            return "%s%02d:%02d"         % (f   ,m,s)
    else:
        if zehntel:
            return "%s%02d:%02d:%02d.%d" % (f, h,m,s,z)
        else:
            return "%s%02d:%02d:%02d"    % (f, h,m,s)

def str2time(s):
    data = list(map(float, s.split(':')))
    sign = -1 if s[0] == '-' else +1
    return sign * sum( abs(d)*60**k for k,d in enumerate(reversed(data)))

def have_latex():
    return have_binary(['pdflatex','-v'])

def is_linux():
    return have_binary(['uname'], 'Linux')

def have_binary(cmd, expect=None):
    try:
        result = subprocess.check_output(cmd).decode()
        return expect is None or expect in result
    except:
        return False


if __name__ == "__main__":
    print( str2time(time2str(-3743.58)) )