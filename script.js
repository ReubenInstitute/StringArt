let isGenerating = false;
let isPaused = false;

function updatePinConstraints() {
	const frameType = document.querySelector('input[name="frameType"]:checked').value;
	const pinsInput = document.getElementById('pins');
	
	pinsInput.setCustomValidity("");
	
	// Handle min/max attributes
	if (frameType === 'svg') {
		pinsInput.removeAttribute('min');
		pinsInput.removeAttribute('max');
	} else {
		pinsInput.min = 100;
		pinsInput.max = 500;
	}

	// Handle validation based on frame type
	if (frameType === 'square') {
		pinsInput.onchange = function() {
			if (this.value % 4 !== 0) {
				this.setCustomValidity("Number of pins must be divisible by 4 for square frames");
			} else {
				this.setCustomValidity("");
			}
		};
	} else if (frameType === 'octagon') {
		pinsInput.onchange = function() {
			if (this.value % 8 !== 0) {
				this.setCustomValidity("Number of pins must be divisible by 8 for octagon frames");
			} else {
				this.setCustomValidity("");
			}
		};
	} else {
		pinsInput.onchange = null;
	}
	
	pinsInput.reportValidity();
}

function togglePause() {
	isPaused = !isPaused;
	document.getElementById('pauseButton').textContent = isPaused ? 'Continue' : 'Pause';
}




async function startGeneration() {
	if (isGenerating) return;

	let size = parseInt(document.getElementById('size').value) || 400;
	size = Math.min(Math.max(size, 100), 2000);
	document.getElementById('size').value = size;
	
	const frameType = document.querySelector('input[name="frameType"]:checked').value;
	const pinsInput = document.getElementById('pins');
	const linesInput = document.getElementById('lines');

	// Validate and correct pin count
	let correctedPins = parseInt(pinsInput.value) || 200;
	if (frameType === 'square') {
		correctedPins = Math.max(100, Math.min(500, Math.round(correctedPins / 4) * 4));
	} else if (frameType === 'octagon') {
		correctedPins = Math.max(100, Math.min(500, Math.round(correctedPins / 8) * 8));
	} else {
		correctedPins = Math.max(1, Math.min(1000, correctedPins));
	}
	pinsInput.value = correctedPins;

	// Validate and correct line count
	let correctedLines = parseInt(linesInput.value) || 1000;
	correctedLines = Math.min(Math.max(correctedLines, 500), 10000);
	linesInput.value = correctedLines;

	// Reset state
	isGenerating = true;
	isPaused = false;
	document.getElementById('pauseButton').textContent = 'Pause';
	document.getElementById('art').innerHTML = '';

	try {
		const formData = new FormData();
		formData.append('frame_type', frameType);
		formData.append('pins', correctedPins);
		formData.append('lines', correctedLines);
		formData.append('size', size);

		const response = await fetch('/generate', {
			method: 'POST',
			body: formData
		});

		if (!response.ok) {
			const error = await response.json();
			alert(`Error: ${error.error}`);
			isGenerating = false;
			return;
		}

		const generateData = await response.json();
		document.getElementById('art').setAttribute('viewBox', `0 0 ${generateData.width} ${generateData.height}`);
   // Update masked image preview
    if (generateData.processed_image) {
        document.getElementById('maskedPreview').src = 
            `data:image/jpeg;base64,${generateData.processed_image}`;
    }
 
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

			// Update status
			document.getElementById('currentStep').textContent = data.step;
			document.getElementById('wireLength').textContent = data.length.toFixed(2);
		}
	} catch (error) {
		alert(`Generation failed: ${error.message}`);
	} finally {
		isGenerating = false;
	}
}

// Initialize constraints when page loads
updatePinConstraints();