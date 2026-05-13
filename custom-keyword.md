# Microsoft Custom Keyword Setup

Use this when creating a Microsoft Custom Keyword wake-word model for the
wake-word endpoint.

## Speech Studio

Open the Custom Keyword page directly:

```text
https://speech.microsoft.com/portal/customkeyword
```

If Microsoft redirects to Custom Speech, go back to the direct Custom Keyword
URL. Custom Speech is for transcription model tuning; Custom Keyword is the
wake-word `.table` model workflow.

## Select Azure Resource

Click **Select a resource** and choose the existing shared-services resource:

```text
Name: wake-word-resources
Resource group: shared-services-rg
Region: eastus2
Kind: AIServices
SKU: S0
```

This avoids creating duplicate paid Azure resources.

## Create Project And Model

1. Click **Create a project**.
2. Project name: `wake-word-demo`.
3. Language: `English (United States)`.
4. Create or open the project.
5. Create a model.
6. Keyword: `Hey Sentinel`.
7. Model type: `Basic`.
8. Start training.

Training can take a few minutes. While training is running, the download action
may not appear.

## Download Model

After training completes:

1. Close the notification panel if it is open.
2. Refresh the model/project page if the status does not update.
3. Select the model row, for example `custom-keyword-demo-model`.
4. Look for **Download** in the toolbar or the row `...` menu.
5. Download the `.zip`.
6. Extract the `.zip`.
7. Find the `.table` file.

Recommended local path:

```bash
mkdir -p /Users/willmacdonald/Documents/Code/claude/wake-word/models
cp /path/to/downloaded-model.table /Users/willmacdonald/Documents/Code/claude/wake-word/models/hey-sentinel.table
```

The `.table` file is the artifact the local Microsoft Speech SDK keyword
recognizer will use for on-device wake-word detection.
