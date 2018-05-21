import serial
from multiprocessing import Process, Pipe
import time


START       = bytes([0xf0])
END         = bytes([0xff])
ACCK        = bytes([0xf1])
ERR         = bytes([0xee])
FAIL        = bytes([0xf2])
CAN_REC     = bytes([0xf4])
SIG_FOUND   = bytes([0xf3])
SIG_FAIL    = bytes([0xfa])

global_bool = True


def test_nlfsr(state, x):
    period = 2**len(state) - 1
    initial = state[:]
    i = 0
    print(state)
    while True:
        i += 1
        feedback = int(state[0]) ^ (int(state[x[0]]) & int(state[x[1]])) ^ int(state[x[2]]) ^ int(state[x[3]]) ^ int(state[x[4]]) ^ int(state[x[5]])
        state = state[1:] + str(feedback)
        print(state)
        if state == initial:
            break
        if i > period:
            break
        if i > 30:
            break
    if i == period:
        return True
    else:
        return False


def change(x):
    x = str(x)
    if len(x) == 7:
        x = x[len(x) - 3] + x[len(x) - 2]
    if len(x) == 6:
        x = x[len(x) - 2]
    return x


def take_poly(poly_file):
    poly1 = poly_file.readline()
    if poly1 == '':
        return -1
    poly1 = poly1[:len(poly1) - 1]
    poly1 = poly1.split(' ')
    poly = []
    for i in poly1:
        poly.append(int(i))
        #print('poly:', poly)
    return poly


def give_polynom(poly_file, count_sent, count_rec):
    poly = take_poly(poly_file)
    if poly == -1:
        print('koniec')
        print(count_sent)
        print(count_rec)
        given = False
        return poly, False, given
    count_sent += 1
    print(count_sent)
    give_poly = False
    given = True
    return poly, give_poly, given, count_sent


def rec_poly(ser1, count_rec, res_file):
    ser1.write(ACCK)  # moge odebrac
    #print('wrote ACCK for receiving poly')
    count_rec += 1
    out = ''
    while True:
        x = ser1.read(size=1)
        #print('received coef: ', x)
        if x == SIG_FOUND:
            continue
        if x == SIG_FAIL:
            continue
        if x == END:
            out = out[:len(out) - 1] + '\n'
            break
        temp = str(change(x))
        if temp is not None:
            out += temp  ############ here temp
            out += ' '
    out += '\n'
    res_file.writelines(out)
    #x = ser1.read(size=1)
    return count_rec


def server(ser1):
    poly_file = open('input.poly', 'r')
    give_poly = True
    res_file = open('results.poly', 'w')
    fail_file = open('failures.poly', 'w')
    count_sent = 0
    count_rec = 0
    while True:
        if give_poly:
            try:
                poly, give_poly, given, count_sent = give_polynom(poly_file, count_sent, count_rec)
            except ValueError:
                break
        t = ser1.read()
        #print(t)
        if t == SIG_FOUND:
            print('SUCCESS')
            count_rec = rec_poly(ser1, count_rec, res_file)
            continue
        if not t:
            ser1.write(START)
            #print('gonna write poly')
            t = ser1.read()
            #print('answer from dev: ', t)
            if t == CAN_REC and given is True:       # fpga can receive
                for i in range(len(poly)):
                    ser1.write(bytes([poly[i]]))
                    #print('poly:', bytes([poly[i]]))
                ser1.write(END)
                #print('wrote poly')
                t = ser1.read(size=1)
                #print('after writting poly - the answer: ', t)
                #print(t)
                if t == ACCK:   # ACCK
                    give_poly = True
                    given = False
                    continue
                else:
                    continue
            elif t == ERR:    #error
                continue
            elif t == SIG_FOUND:
                print('SUCCESS')
                count_rec = rec_poly(ser1, count_rec, res_file)
                continue
            elif t == SIG_FAIL:
                count_rec = rec_poly(ser1, count_rec, fail_file)
                continue
        if t == SIG_FAIL:
            count_rec = rec_poly(ser1, count_rec, fail_file)
            continue
    while count_rec < count_sent:
        t = ser1.read()
        if t == SIG_FOUND:
            count_rec = rec_poly(ser1, count_rec, res_file)
            continue
        if t == SIG_FAIL:
            count_rec = rec_poly(ser1, count_rec, fail_file)
            continue
    print(count_rec)



if __name__ == '__main__':
    try:
        ser1 = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.05)
        ser1.close()
        ser1.open()
        Server = Process(target=server, args=(ser1,))
        Server.start()
        Server.join()
        # state = '100000000000000000000000'
        # x = [7,18,1,8,9,15]
        # test_nlfsr(state, x)
    except KeyboardInterrupt:
        print('Przerwano z klawiatury')
        ser1.close()
