let isGenerating = false;

function updatePinConstraints() {
	const frameType = document.querySelector('input[name="frameType"]:checked').value;
	const pinsInput = document.getElementById('pins');

	pinsInput.setCustomValidity("");

	// Handle min/max attributes - circle/square/octagon are pin-constrained,
	// any other value is an SVG shape file with no pin-count constraint
	const pinConstrainedShapes = ['circle', 'square', 'octagon'];
	if (!pinConstrainedShapes.includes(frameType)) {
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

function getSelectedFile() {
	const selectedFileInput = document.querySelector('input[name="selectedFile"]:checked');
	return selectedFileInput ? selectedFileInput.value : null;
}

// While idle, refresh just the masked-image preview to reflect the
// currently selected file/shape - does not touch /next_step or the art canvas.
async function refreshMaskedPreview() {
	if (isGenerating) return;

	const selectedFile = getSelectedFile();
	if (!selectedFile) return;

	const frameType = document.querySelector('input[name="frameType"]:checked').value;
	const pins = parseInt(document.getElementById('pins').value) || 200;
	const lines = parseInt(document.getElementById('lines').value) || 1000;
	const size = parseInt(document.getElementById('size').value) || 400;

	const formData = new FormData();
	formData.append('frame_type', frameType);
	formData.append('selected_file', selectedFile);
	formData.append('pins', pins);
	formData.append('lines', lines);
	formData.append('size', size);

	try {
		const response = await fetch('/generate', {
			method: 'POST',
			body: formData
		});
		if (!response.ok) return;

		const generateData = await response.json();
		if (generateData.processed_image) {
			document.getElementById('maskedPreview').src =
				`data:image/jpeg;base64,${generateData.processed_image}`;
		}
	} catch (error) {
		// Preview is best-effort; ignore failures here.
	}
}

// Enables/disables everything except the Generate/Stop button itself.
function setControlsDisabled(disabled) {
	document.querySelectorAll('#generateForm input').forEach(el => el.disabled = disabled);
	document.querySelectorAll('#uploadForm input, #uploadForm button').forEach(el => el.disabled = disabled);
}

async function toggleGeneration() {
	if (isGenerating) {
		stopGeneration();
	} else {
		await startGeneration();
	}
}

function stopGeneration() {
	isGenerating = false;
	setControlsDisabled(false);
	document.getElementById('generateButton').textContent = 'Generate';
}

async function startGeneration() {
	const selectedFile = getSelectedFile();
	if (!selectedFile) {
		alert('Please upload and select an image first!');
		return;
	}

	const frameType = document.querySelector('input[name="frameType"]:checked').value;
	const pinsInput = document.getElementById('pins');
	const linesInput = document.getElementById('lines');

	let size = parseInt(document.getElementById('size').value) || 400;
	size = Math.min(Math.max(size, 100), 2000);
	document.getElementById('size').value = size;

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

	// Lock everything else and switch the button to "Stop"
	isGenerating = true;
	setControlsDisabled(true);
	document.getElementById('generateButton').textContent = 'Stop';
	document.getElementById('art').innerHTML = '';
	document.getElementById('currentStep').textContent = '0';
	document.getElementById('wireLength').textContent = '0.00';

	try {
		const formData = new FormData();
		formData.append('frame_type', frameType);
		formData.append('selected_file', selectedFile);
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
			stopGeneration();
			return;
		}

		const generateData = await response.json();
		document.getElementById('art').setAttribute('viewBox', `0 0 ${generateData.width} ${generateData.height}`);
		if (generateData.processed_image) {
			document.getElementById('maskedPreview').src =
				`data:image/jpeg;base64,${generateData.processed_image}`;
		}

		while (isGenerating) {
			const stepResponse = await fetch('/next_step');
			if (!stepResponse.ok) break;

			const data = await stepResponse.json();

			if (data.done) {
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
		stopGeneration();
	}
}

// Changing the selected file or shape while idle updates the masked-image
// preview immediately, without starting generation.
document.addEventListener('change', (e) => {
	if (!e.target) return;
	if (e.target.name === 'selectedFile' || e.target.name === 'frameType') {
		refreshMaskedPreview();
	}
});

// Initialize constraints when page loads
updatePinConstraints();
