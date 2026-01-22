---
name: powerpoint-generator
description: Generate PowerPoint presentations from user requirements
version: 1.0.0
author: Agent Skills Framework
license: MIT
allowed-tools: "Bash(python:*),Read,Write"
activation_mode: auto
max_execution_time: 300
network_access: false
python_packages:
  - python-pptx>=0.6.21
system_packages: []
output_type: file
output_formats:
  - pptx
metadata:
  category: productivity
  tags: powerpoint,presentation,pptx,slides
---

# PowerPoint Generator Skill

**CRITICAL: You MUST use bash_tool to actually create PowerPoint files. Do not just describe the content - execute the script!**

You are now equipped to generate PowerPoint presentations using the `create_presentation.py` script.

## IMPORTANT: How to Actually Create Files

When a user asks you to create a PowerPoint:

1. **DO NOT** just describe what the presentation would contain
2. **DO** use bash_tool to execute the create_presentation.py script
3. **DO** actually generate the .pptx file

**Example of CORRECT behavior:**
```
User: "Create a 3 slide presentation about AI"
You: *calls bash_tool with the script* → File is created → "I've created your presentation!"
```

**Example of INCORRECT behavior:**
```
User: "Create a 3 slide presentation about AI"  
You: "Here's what the presentation would contain..." → NO FILE CREATED ❌
```

## How to Use bash_tool

Use **bash_tool** to execute the PowerPoint generation script with appropriate arguments.

### Basic Usage

```bash
bash_tool("python {baseDir}/scripts/create_presentation.py --title 'My Presentation' --subtitle 'Created with AI' --slides 'Slide 1|Content for slide 1' 'Slide 2|Content for slide 2' --output presentation.pptx")
```

### Script Arguments

- `--title` (required): Presentation title
- `--subtitle` (optional): Presentation subtitle  
- `--slides` (required): One or more slides in format "Title|Content"
  - Use `\n` in content for bullet points
  - Example: `"Slide Title|Point 1\nPoint 2\nPoint 3"`
- `--output` (optional): Output filename (default: presentation.pptx)
- `--output-dir` (optional): Output directory

## Example: 3-Slide Presentation

```bash
bash_tool("""python {baseDir}/scripts/create_presentation.py \
  --title "Environmental Impact of AI" \
  --subtitle "Understanding the Carbon Footprint" \
  --slides \
    "Energy Consumption|Training large AI models requires significant energy\nGPT-3 training: ~1,287 MWh of electricity\nEquivalent to 120 homes for a year" \
    "Carbon Emissions|Data centers contribute to CO2 emissions\nCooling systems require additional energy\nLocation matters: renewable vs fossil fuel grids" \
    "Solutions|Use renewable energy for data centers\nOptimize model efficiency\nShare pre-trained models\nImplement green AI practices" \
  --output ai_environmental_impact.pptx
""")
```

## File Output Protocol

When generating presentations for download:

1. **Save to output directory**:
   ```bash
   bash_tool("""python {baseDir}/scripts/create_presentation.py \
     --title "My Presentation" \
     --slides "Slide 1|Content" \
     --output-dir /tmp/skill_outputs/{session_id} \
     --output presentation.pptx
   """)
   ```

2. The script automatically prints the FILE_OUTPUT marker when saving to `/tmp/skill_outputs/`

3. Provide a friendly message:
   "I've created your presentation! Click the download button below."

## Content Formatting Tips

### Bullet Points
Use `\n` to separate bullet points:
```bash
--slides "Title|First point\nSecond point\nThird point"
```

### Multiple Slides
Provide multiple slide arguments:
```bash
--slides "Slide 1|Content 1" "Slide 2|Content 2" "Slide 3|Content 3"
```

### Empty Content
For slides with just a title:
```bash
--slides "Title Only|" "Another Title|"
```

## Common Patterns

### Simple 3-Slide Deck
```bash
bash_tool("""python {baseDir}/scripts/create_presentation.py \
  --title "Presentation Title" \
  --subtitle "Subtitle" \
  --slides \
    "Introduction|Overview of the topic\nKey points to cover" \
    "Main Content|Detailed information\nSupporting data\nExamples" \
    "Conclusion|Summary of key takeaways\nNext steps" \
  --output presentation.pptx
""")
```

### Marketing Presentation
```bash
bash_tool("""python {baseDir}/scripts/create_presentation.py \
  --title "Product Launch" \
  --subtitle "Q1 2024" \
  --slides \
    "Market Opportunity|Target audience: 50M users\nMarket size: $2B\nGrowth rate: 25% YoY" \
    "Product Features|Feature 1: AI-powered\nFeature 2: Cloud-based\nFeature 3: Mobile-first" \
    "Go-to-Market|Launch date: March 1\nChannels: Digital, retail\nBudget: $5M" \
  --output product_launch.pptx
""")
```

## Error Handling

The script includes error handling for:
- Missing python-pptx library
- Invalid arguments
- File write permissions
- Empty slides

If you encounter errors, check:
1. python-pptx is installed: `pip install python-pptx`
2. Arguments are properly quoted
3. Output directory exists and is writable

## Dependencies

Requires: `python-pptx>=0.6.21`

Install with:
```bash
pip install python-pptx
```
