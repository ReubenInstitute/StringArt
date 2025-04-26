let isGenerating = false;
let isPaused = false;

function updatePinConstraints() {
    const frameType = document.querySelector('input[name="frameType"]:checked').value;
    const pinsInput = document.getElementById('pins');
    
    if (frameType === 'square') {
        pinsInput.min = 100;
        pinsInput.step = 4;
        if (pinsInput.value % 4 !== 0) {
            pinsInput.value = Math.round(pinsInput.value / 4) * 4;
        }
    } else {
        pinsInput.min = 100;
        pinsInput.step = 1;
    }
    
    pinsInput.value = Math.min(Math.max(pinsInput.value, pinsInput.min), pinsInput.max);
}

function togglePause() {
    isPaused = !isPaused;
    document.getElementById('pauseButton').textContent = isPaused ? 'Continue' : 'Pause';
}

async function startGeneration() {
    if (isGenerating) return;
    
    const frameType = document.querySelector('input[name="frameType"]:checked').value;
    const pinsInput = document.getElementById('pins');
    const linesInput = document.getElementById('lines');

    let correctedPins = parseInt(pinsInput.value) || 200;
    correctedPins = Math.min(Math.max(correctedPins, 100), 500);
    if (frameType === 'square') {
        correctedPins = Math.round(correctedPins / 4) * 4;
    }
    pinsInput.value = correctedPins;

    let correctedLines = parseInt(linesInput.value) || 1000;
    correctedLines = Math.min(Math.max(correctedLines, 500), 10000);
    linesInput.value = correctedLines;

    isGenerating = true;
    isPaused = false;
    document.getElementById('pauseButton').textContent = 'Pause';
    document.getElementById('art').innerHTML = '';

    const formData = new FormData();
    formData.append('frame_type', frameType);
    formData.append('pins', correctedPins);
    formData.append('lines', correctedLines);

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            console.error('Server error:', error);
            isGenerating = false;
            return;
        }

        const generateData = await response.json();
        const artWidth = generateData.width;
        const artHeight = generateData.height;
        document.getElementById('art').setAttribute('viewBox', `0 0 ${artWidth} ${artHeight}`);

        while (isGenerating) {
            if (isPaused) {
                await new Promise(r => setTimeout(r, 100));
                continue;
            }

            const stepResponse = await fetch('/next_step');
            if (!stepResponse.ok) break;
            
            const data = await stepResponse.json();
            
            if (data.done) {
                isGenerating = false;
                break;
            }

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', data.x0);
            line.setAttribute('y1', data.y0);
            line.setAttribute('x2', data.x1);
            line.setAttribute('y2', data.y1);
            line.setAttribute('stroke', 'black');
            line.setAttribute('stroke-width', '0.5');
            document.getElementById('art').appendChild(line);

            document.getElementById('currentStep').textContent = data.step;
            document.getElementById('wireLength').textContent = data.length.toFixed(2);
        }
    } catch (error) {
        console.error('Generation error:', error);
    } finally {
        isGenerating = false;
    }
}

updatePinConstraints();