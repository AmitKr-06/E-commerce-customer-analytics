/* --------------------------------------------------
   Get HTML elements
-------------------------------------------------- */

const predictionForm = document.getElementById("prediction-form");

const predictButton = document.getElementById("predict-button");
const buttonText = document.getElementById("button-text");

const emptyResult = document.getElementById("empty-result");
const loadingState = document.getElementById("loading-state");
const predictionOutput = document.getElementById("prediction-output");

const errorMessage = document.getElementById("error-message");
const errorText = document.getElementById("error-text");

const warningsSection = document.getElementById("warnings-section");
const warningsList = document.getElementById("warnings-list");


/* --------------------------------------------------
   Input field types
-------------------------------------------------- */

const intFields = [
    "customer_zip",
    "seller_zip",
    "n_items",
    "n_sellers"
];

const numberFields = [
    "est_days",
    "items_price",
    "freight",
    "weight_g"
];

const stringFields = [
    "customer_state",
    "seller_state",
    "main_category",
    "purchase_datetime"
];


/* --------------------------------------------------
   Convert form values into API payload
-------------------------------------------------- */

function preparePayload(formData) {

    const payload = {};

    intFields.forEach((field) => {
        const value = formData.get(field);
        payload[field] = (value === null || value.trim() === "")
            ? null
            : Number.parseInt(value, 10);
    });

    numberFields.forEach((field) => {
        const value = formData.get(field);
        payload[field] = (value === null || value.trim() === "")
            ? null
            : Number.parseFloat(value);
    });

    stringFields.forEach((field) => {
        const value = formData.get(field);
        payload[field] = (value === null || value.trim() === "")
            ? null
            : value;
    });

    return payload;
}


/* --------------------------------------------------
   Show loading state
-------------------------------------------------- */

function showLoading() {
    emptyResult.classList.add("hidden");
    predictionOutput.classList.add("hidden");
    errorMessage.classList.add("hidden");

    loadingState.classList.remove("hidden");

    predictButton.disabled = true;
    buttonText.textContent = "Predicting...";
}


/* --------------------------------------------------
   Show prediction result
-------------------------------------------------- */

function showResult(data) {
    loadingState.classList.add("hidden");
    emptyResult.classList.add("hidden");
    errorMessage.classList.add("hidden");

    predictionOutput.classList.remove("hidden");

    document.getElementById("predicted-days").textContent =
        Number(data.predicted_days).toFixed(1);

    document.getElementById("predicted-date").textContent =
        data.predicted_delivery_date;

    document.getElementById("platform-days").textContent =
        `${Number(data.platform_estimate_days).toFixed(1)} days`;

    document.getElementById("model-days").textContent =
        `${Number(data.predicted_days).toFixed(1)} days`;

    const difference = Number(data.platform_minus_model_days);

    document.getElementById("difference-days").textContent =
        `${difference > 0 ? "+" : ""}${difference.toFixed(1)} days`;

    const comparisonMessage =
        document.getElementById("comparison-message");

    if (difference > 0) {
        comparisonMessage.textContent =
            `The platform estimate is ${difference.toFixed(1)} days longer than the model prediction.`;
    } else if (difference < 0) {
        comparisonMessage.textContent =
            `The model predicts ${Math.abs(difference).toFixed(1)} more days than the platform estimate.`;
    } else {
        comparisonMessage.textContent = "Both estimates are equal.";
    }

    document.getElementById("model-trained-on").textContent =
        data.model_trained_on;

    warningsList.innerHTML = "";

    const warnings = Array.isArray(data.warnings) ? data.warnings : [];

    if (warnings.length > 0) {
        warnings.forEach((warning) => {
            const listItem = document.createElement("li");
            listItem.textContent = warning;
            warningsList.appendChild(listItem);
        });
        warningsSection.classList.remove("hidden");
    } else {
        warningsSection.classList.add("hidden");
    }
}


/* --------------------------------------------------
   Show error message
-------------------------------------------------- */

function showError(message) {
    loadingState.classList.add("hidden");
    emptyResult.classList.add("hidden");
    predictionOutput.classList.add("hidden");

    errorMessage.classList.remove("hidden");
    errorText.textContent = message;
}


/* --------------------------------------------------
   Handle FastAPI validation and server errors
-------------------------------------------------- */

function getErrorMessage(data) {
    if (Array.isArray(data.detail)) {
        return data.detail.map((error) => {
            const field = error.loc?.at(-1) || "input";
            return `${field}: ${error.msg}`;
        }).join("\n");
    }
    return data.detail || data.error || "Prediction failed.";
}


/* --------------------------------------------------
   Submit prediction form
-------------------------------------------------- */

predictionForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!predictionForm.checkValidity()) {
        predictionForm.reportValidity();
        return;
    }

    const formData = new FormData(predictionForm);
    const payload = preparePayload(formData);

    showLoading();

    try {
        const response = await fetch("/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(getErrorMessage(data));
        }

        showResult(data);

    } catch (error) {
        console.error("Prediction error:", error);
        showError(error.message || "Something went wrong. Please try again.");

    } finally {
        predictButton.disabled = false;
        buttonText.textContent = "Predict Delivery Time";
    }
});


/* --------------------------------------------------
   Reset form and prediction output
-------------------------------------------------- */

document.getElementById("reset-button").addEventListener("click", () => {
    predictionForm.reset();

    loadingState.classList.add("hidden");
    predictionOutput.classList.add("hidden");
    errorMessage.classList.add("hidden");
    warningsSection.classList.add("hidden");

    emptyResult.classList.remove("hidden");
});