import math
import numpy as np
from prepare_rul import load_train

# Функция износа датчиков: f1(t) = a + b * exp(c / 100 * t)
# Функция минимизации: Σ(s11(t) - f1(t))^2

df = load_train('/Users/albert/Desktop/vuz/kpo/predictive-ml-model/data/train_FD001.txt')
engine = df[df['unit'] == 81]
part = engine[engine['cycle'] <= 200]
t_values = part['cycle'].tolist()
s11_values = part['s11'].tolist()

def f(a, b, c, t):
    return a + b * math.exp(c / 100 * t)

def err(a, b, c):
    sum = 0

    for t, s11 in zip(t_values, s11_values):
        model = f(a, b, c, t)
        sum += (s11 - model) ** 2
    return sum

def hessian(err, point, h=1e-5):
    a, b, c = point
    H = [[0]*3 for _ in range(3)]

    H[0][0] = (err(a+h, b, c) - 2*err(a, b, c) + err(a-h, b, c)) / (h**2)
    H[1][1] = (err(a, b+h, c) - 2*err(a, b, c) + err(a, b-h, c)) / (h**2)
    H[2][2] = (err(a, b, c+h) - 2*err(a, b, c) + err(a, b, c-h)) / (h**2)

    H[0][1] = H[1][0] = (err(a+h, b+h, c) - err(a+h, b-h, c) - err(a-h, b+h, c) + err(a-h, b-h, c)) / (4 * h**2)
    H[0][2] = H[2][0] = (err(a+h, b, c+h) - err(a+h, b, c-h) - err(a-h, b, c+h) + err(a-h, b, c-h)) / (4 * h**2)
    H[1][2] = H[2][1] = (err(a, b+h, c+h) - err(a, b+h, c-h) - err(a, b-h, c+h) + err(a, b-h, c-h)) / (4 * h**2)

    return H


def golden(phi, L, R, eps=1e-6):
    k = 0.618
    while R - L > eps:
        t1 = R - k * (R - L)
        t2 = L + k * (R - L)
        if phi(t1) < phi(t2):
            R = t2
        else:
            L = t1
    return (L + R) / 2

def ops(point, eps=1e-6):
    while True:
        a, b, c = point

        old_a = a
        old_b = b
        old_c = c

        H = hessian(err, point)

        eigenvalues, eigenvectors = np.linalg.eigh(H)

        for i in range (3):
            eigenvector = eigenvectors[:, i]
            phi = lambda t: err(a + eigenvector[0] * t, b + eigenvector[1] * t, c + eigenvector[2] * t)
            t = golden(phi, -1, 1)
            a = a + eigenvector[0] * t
            b = b + eigenvector[1] * t
            c = c + eigenvector[2] * t
            point = (a, b, c)

        shift = math.sqrt((a - old_a)**2 + (b - old_b)**2 + (c - old_c)**2)

        if shift < eps:
            return point


if __name__ == "__main__" :
    a = 47.53
    b = 0.01
    c = 0.01
    point = (a, b, c)
    new_point = ops(point)
    s11_predicted = new_point[0] + new_point[1] * math.exp(new_point[2] / 100 * 238)
    print(s11_predicted)







