$(function () {
    const cube = $(".cube").cube({
        animation: {
            delay: 100
        }
    });
    let bufferMoves = null

    $("#play").click(() => {
        const moves = $('#moves').val()
        if (!moves) {
            alert("Please input scarmble or use Auto Scramble")
            return
        }
        cube.execute(moves)
        $("#moves").prop('disabled', true)
        $("#play").prop('disabled', true)
    })

    $("#autoScramble").click(async () => {
        $("#autoScramble").prop('disabled', true)
        try {
            const response = await fetch('http://127.0.0.1:5000/auto')
            const data = await response.json();
            $("#moves").prop('value', data)
        } catch (err) {
            console.log(err);
        }
        $("#autoScramble").prop('disabled', false)
    })

    let rangeInput = $("#turnSpeed")[0]
    $("#turnSpeed").change(() => {
        let value = rangeInput.value
        let max = parseInt(rangeInput.max)
        let min = parseInt(rangeInput.min)
        value = (max + min) - value
        cube.changeSpeed(value);
    })

    $("#reset").click(() => {
        cube.reset()
        $("#moves").prop('disabled', false)
        $("#play").prop('disabled', false)
        $("#submit").prop("disabled", false)
        $("#result").html("")
        cube.data("move-stack", null)
    })

    $("#pause").click(() => {
        let moves = cube.data("move-stack")
        if (!moves)
            return
        bufferMoves = moves.slice()
        cube.data("move-stack", null)
    })

    $("#resume").click(() => {
        if (!bufferMoves)
            return
        cube.data("move-stack", bufferMoves)
        bufferMoves = null
        cube.trigger("next-move")
    })


    $('#submit').click(async () => {
        const moves = $('#moves').val()
        if (!$("#play").prop("disabled")) {
            alert("Scramble the rubik's cube frist")
            return
        }
        $("#result").html('Solving...')
        $("#submit").prop("disabled", true)
        requestData = {
            moves: moves
        }
        try {
            const response = await fetch('http://127.0.0.1:5000/move', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            // console.log(response);
            const data = await response.json();
            // console.log(data);

            const { cross, f2l, oll, pll } = data

            if (cross['done']) {
                cube.execute(cross['moves'].join(" "));
            } else {
                cross['moves'] = "Not solve"
            }

            if (f2l['done']) {
                cube.execute(f2l['moves'].join(" "))
            } else {
                f2l['moves'] = "Not Solve"
            }

            crossMovesCount = cross['movesCount']
            f2lMovesCount = f2l['movesCount']
            ollMovesCount = oll['movesCount']
            pllMovesCount = pll['movesCount']
            if (ollMovesCount > 0)
                cube.execute(oll['moves'])

            if (pllMovesCount > 0)
                cube.execute(pll['moves'])


            let crossResult = `<p>Cross(${crossMovesCount} moves): ${cross['moves']}</p>`
            let f2lResult = `<p>F2L(${f2lMovesCount} moves): ${f2l['moves']}</p>`
            let ollResult = `<p>OLL(${ollMovesCount} moves): ${oll['moves']}</p>`
            let pllResult = `<p>PLL(${pllMovesCount} moves): ${pll['moves']}</p>`
            let totalMovesCount = crossMovesCount + f2lMovesCount + ollMovesCount + pllMovesCount
            let finalResult = crossResult + f2lResult + ollResult + pllResult +
                `<p>Total moves: ${totalMovesCount}</p>`

            $('#result').html(finalResult)

        } catch (err) {
            console.log(err);
        }

    })
})