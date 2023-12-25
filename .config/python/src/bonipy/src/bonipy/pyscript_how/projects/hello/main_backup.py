#!/usr/bin/env python3

# Standard libraries
import asyncio

# External dependencies.
import js
import numpy as np
import pyodide.ffi
import pyscript
import pyweb.pydom
import sympy

# Internal modules.
from palettes import Magma256
from fractals import mandelbrot, julia, newton


def prepare_canvas(
    width: int, height: int, canvas: pyweb.pydom.Element
) -> js.CanvasRenderingContext2D:
    ctx = canvas._js.getContext("2d")

    canvas.style["width"] = f"{width}px"
    canvas.style["height"] = f"{height}px"

    canvas._js.width = width
    canvas._js.height = height

    ctx.clearRect(0, 0, width, height)

    return ctx


def color_map(array: np.array, palette: np.array) -> np.array:
    size, _ = palette.shape
    index = (array / array.max() * (size - 1)).round().astype("uint8")

    width, height = array.shape
    image = np.full((width, height, 4), 0xFF, dtype=np.uint8)
    image[:, :, :3] = palette[index]

    return image


def draw_image(ctx: js.CanvasRenderingContext2D, image: np.array) -> None:
    data = js.Uint8ClampedArray.new(pyodide.ffi.to_js(image.tobytes()))
    width, height, _ = image.shape
    image_data = js.ImageData.new(data, width, height)
    ctx.putImageData(image_data, 0, 0)


async def draw_mandelbrot(width, height) -> None:
    spinner = pyweb.pydom["#mandelbrot .loading"]
    canvas = pyweb.pydom["#mandelbrot canvas"][0]

    spinner.style["display"] = ""
    canvas.style["display"] = "none"

    ctx = prepare_canvas(width, height, canvas)

    js.console.log("Computing Mandelbrot set ...")
    js.console.time("mandelbrot")
    iters = mandelbrot(width, height)
    js.console.timeEnd("mandelbrot")

    image = color_map(iters, Magma256)
    draw_image(ctx, image)

    spinner.style["display"] = "none"
    canvas.style["display"] = "block"


async def draw_julia(width, height) -> None:
    spinner = pyweb.pydom["#julia .loading"]
    canvas = pyweb.pydom["#julia canvas"][0]

    spinner.style["display"] = ""
    canvas.style["display"] = "none"

    ctx = prepare_canvas(width, height, canvas)

    js.console.log("Computing Julia set ...")
    js.console.time("julia")
    iters = julia(width, height)
    js.console.timeEnd("julia")

    image = color_map(iters, Magma256)
    draw_image(ctx, image)

    spinner.style["display"] = "none"
    canvas.style["display"] = "block"


def ranges():
    x0_in = pyweb.pydom["#x0"][0]
    x1_in = pyweb.pydom["#x1"][0]
    y0_in = pyweb.pydom["#y0"][0]
    y1_in = pyweb.pydom["#y1"][0]

    xr = (float(x0_in.value), float(x1_in.value))
    yr = (float(y0_in.value), float(y1_in.value))

    return xr, yr


current_image = None


async def draw_newton(width, height) -> None:
    spinner = pyweb.pydom["#newton .loading"]
    canvas = pyweb.pydom["#newton canvas"][0]

    spinner.style["display"] = ""
    canvas.style["display"] = "none"

    ctx = prepare_canvas(width, height, canvas)

    js.console.log("Computing Newton set ...")

    poly_in = pyweb.pydom["#poly"][0]
    coef_in = pyweb.pydom["#coef"][0]
    conv_in = pyweb.pydom["#conv"][0]

    xr, yr = ranges()

    expr = sympy.parse_expr(poly_in.value)
    coeffs = [
        complex(c) for c in reversed(sympy.Poly(expr, sympy.Symbol("z")).all_coeffs())
    ]
    poly = np.polynomial.Polynomial(coeffs)

    coef = complex(sympy.parse_expr(coef_in.value))

    js.console.time("newton")
    iters, roots = newton(width, height, p=poly, a=coef, xr=xr, yr=yr)
    js.console.timeEnd("newton")

    if conv_in._js.checked:
        n = poly.degree() + 1
        k = int(len(Magma256) / n)

        colors = Magma256[::k, :][:n]
        colors[0, :] = [255, 0, 0]  # red: no convergence

        image = color_map(roots, colors)
    else:
        image = color_map(iters, Magma256)

    global current_image
    current_image = image
    draw_image(ctx, image)

    spinner.style["display"] = "none"
    canvas.style["display"] = "block"


newton_fieldset = pyweb.pydom["#newton fieldset"]


@pyscript.when("change", newton_fieldset)
async def fieldset_rerender(event):
    await draw_newton(width, height)


width, height = 600, 600
canvas = pyweb.pydom["#newton canvas"][0]

is_selecting = False
init_sx, init_sy = None, None
sx, sy = None, None


@pyscript.when("mousemove", canvas)
async def mousemove(event):
    global is_selecting
    global init_sx
    global init_sy
    global sx
    global sy

    def invert(sx, source_range, target_range):
        source_start, source_end = source_range
        target_start, target_end = target_range
        factor = (target_end - target_start) / (source_end - source_start)
        offset = -(factor * source_start) + target_start
        return (sx - offset) / factor

    bds = canvas._js.getBoundingClientRect()
    event_sx, event_sy = event.clientX - bds.x, event.clientY - bds.y

    ctx = canvas._js.getContext("2d")

    pressed = event.buttons == 1
    if is_selecting:
        if not pressed:
            xr, yr = ranges()

            x0 = invert(init_sx, xr, (0, width))
            x1 = invert(sx, xr, (0, width))
            y0 = invert(init_sy, yr, (0, height))
            y1 = invert(sy, yr, (0, height))

            pyweb.pydom["#x0"][0].value = x0
            pyweb.pydom["#x1"][0].value = x1
            pyweb.pydom["#y0"][0].value = y0
            pyweb.pydom["#y1"][0].value = y1

            is_selecting = False
            init_sx, init_sy = None, None
            sx, sy = init_sx, init_sy

            await draw_newton(width, height)
        else:
            ctx.save()
            ctx.clearRect(0, 0, width, height)
            draw_image(ctx, current_image)
            sx, sy = event_sx, event_sy
            ctx.beginPath()
            ctx.rect(init_sx, init_sy, sx - init_sx, sy - init_sy)
            ctx.fillStyle = "rgba(255, 255, 255, 0.4)"
            ctx.strokeStyle = "rgba(255, 255, 255, 1.0)"
            ctx.fill()
            ctx.stroke()
            ctx.restore()
    else:
        if pressed:
            is_selecting = True
            init_sx, init_sy = event_sx, event_sy
            sx, sy = init_sx, init_sy


async def main():
    _ = await asyncio.gather(
        draw_mandelbrot(width, height),
        draw_julia(width, height),
        draw_newton(width, height),
    )


asyncio.ensure_future(main())
