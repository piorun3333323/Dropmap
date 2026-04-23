from flask import Flask, render_template, request, jsonify, redirect, session
import math
from PIL import Image

app = Flask(__name__)
app.secret_key = "secret123"

PASSWORD = "43214321123"

heightmap = Image.open("static/heightmap.png").convert("L")
MAP_W, MAP_H = heightmap.size

PIXELS_PER_METER = 0.25

BUS_SPEED = 50
DIVE_SPEED = 75
GLIDE_SPEED = 25
FALL_SPEED = 20

DEPLOY_BASE = 110


def get_height(x, y):
    px = int(x * MAP_W)
    py = int(y * MAP_H)

    px = max(0, min(MAP_W - 1, px))
    py = max(0, min(MAP_H - 1, py))

    value = heightmap.getpixel((px, py))
    return (value / 255) * 100


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["logged"] = True
            return redirect("/menu")
    return render_template("login.html")


@app.route("/menu")
def menu():
    if not session.get("logged"):
        return redirect("/")
    return render_template("menu.html")


@app.route("/calculator")
def calculator():
    if not session.get("logged"):
        return redirect("/")
    return render_template("index.html")


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json

    lx, ly = data["landing"]["x"], data["landing"]["y"]
    x1, y1 = data["bus1"]["x"], data["bus1"]["y"]
    x2, y2 = data["bus2"]["x"], data["bus2"]["y"]

    dx = x2 - x1
    dy = y2 - y1

    best = None
    best_score = 999999

    for i in range(1000):
        t = i / 1000

        bx = x1 + dx * t
        by = y1 + dy * t

        dist = math.hypot(lx - bx, ly - by)
        dist_m = dist * (MAP_W / PIXELS_PER_METER)

        terrain = get_height(lx, ly)
        deploy_height = max(70, min(120, DEPLOY_BASE - terrain))

        dive_range = deploy_height * 2.8
        glide_range = 300 + deploy_height

        ideal_dist = dive_range + glide_range
        dist_penalty = abs(dist_m - ideal_dist)

        fall_time = (
            deploy_height / FALL_SPEED +
            dive_range / DIVE_SPEED +
            glide_range / GLIDE_SPEED
        )

        bus_dist = math.hypot(bx - x1, by - y1) * (MAP_W / PIXELS_PER_METER)
        bus_time = bus_dist / BUS_SPEED

        total_time = fall_time + bus_time
        score = total_time + dist_penalty * 0.05

        if score < best_score:
            best_score = score

            # 🔥 FINAL FIX (BLISKO + DALEKO)
            if dist_m < 600:
                ratio = 0.75 + (dist_m / 600) * 0.15
            else:
                ratio = dive_range / (dist_m + 1)
                ratio = max(0.5, min(0.85, ratio))

            best = {
                "jump_x": bx,
                "jump_y": by,
                "deploy_x": bx + (lx - bx) * ratio,
                "deploy_y": by + (ly - by) * ratio,
                "distance": int(dist_m),
                "time": round(total_time, 2)
            }

    return jsonify(best)


if __name__ == "__main__":
    app.run(debug=True)