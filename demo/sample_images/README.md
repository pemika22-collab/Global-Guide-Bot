# Sample Images for Demo

These images are used to demonstrate the image-based booking flow with Amazon Nova Act.

## Images Included

### 1. bangkok_temple.jpg
- **Location:** Wat Arun (Temple of Dawn), Bangkok
- **Type:** Buddhist Temple
- **Use Case:** Temple tour booking
- **Features:** Iconic riverside temple with ornate spires
- **Best For:** Cultural tours, photography, architecture enthusiasts
- **Demo Flow:** Tourist uploads temple photo → AI detects Bangkok → Matches temple guides

### 2. pattaya_beach.jpg
- **Location:** Pattaya Beach
- **Type:** Beach/Coastal
- **Use Case:** Beach tour booking
- **Features:** Sandy beach, water activities
- **Best For:** Beach tours, water sports, relaxation
- **Demo Flow:** Tourist uploads beach photo → AI detects Pattaya → Matches beach guides

### 3. phuket_beach.jpg
- **Location:** Phuket Beach
- **Type:** Beach/Coastal
- **Use Case:** Island tour booking
- **Features:** Tropical beach, clear water
- **Best For:** Island hopping, diving, beach activities
- **Demo Flow:** Tourist uploads beach photo → AI detects Phuket → Matches island guides

## How to Use

### In Demo Scripts
```python
# Flow 2: Image-based booking
image_path = "demo/sample_images/bangkok_temple.jpg"
```

### In WhatsApp Testing
1. Send any of these images to your WhatsApp Business number
2. The system will analyze the image using Amazon Nova Act
3. Location and interests will be automatically extracted
4. Relevant guides will be matched

### Testing Different Scenarios

**Scenario 1: Temple Tour**
```bash
# Use bangkok_temple.jpg
# Expected: Matches temple/culture guides in Bangkok
```

**Scenario 2: Beach Tour (Pattaya)**
```bash
# Use pattaya_beach.jpg
# Expected: Matches beach/water sports guides in Pattaya
```

**Scenario 3: Island Tour (Phuket)**
```bash
# Use phuket_beach.jpg
# Expected: Matches island/diving guides in Phuket
```

## Image Analysis Results

### Bangkok Temple
```json
{
  "location": "Bangkok",
  "landmark": "Wat Arun",
  "type": "temple",
  "interests": ["culture", "temples", "architecture", "photography"],
  "suggested_guides": "Temple specialists, cultural guides"
}
```

### Pattaya Beach
```json
{
  "location": "Pattaya",
  "type": "beach",
  "interests": ["beach", "water sports", "relaxation"],
  "suggested_guides": "Beach guides, water sports instructors"
}
```

### Phuket Beach
```json
{
  "location": "Phuket",
  "type": "beach",
  "interests": ["island hopping", "diving", "beaches"],
  "suggested_guides": "Island tour guides, diving instructors"
}
```

## Adding Your Own Images

To test with your own images:

1. Add image to this folder
2. Update demo script to use your image path
3. Run the demo

**Supported formats:** JPG, JPEG, PNG
**Max size:** 5MB (WhatsApp limit)

## Technical Details

### Image Processing Flow
1. Image uploaded via WhatsApp or demo script
2. Stored in S3 bucket
3. Analyzed by Amazon Nova Act (vision model)
4. Location and interests extracted
5. Guides matched using semantic search
6. Results returned to user

### Models Used
- **Amazon Nova Act:** Image understanding and location extraction
- **Nova Pro:** Semantic guide matching
- **Claude 3.5 Sonnet:** Orchestration

## Tips for Best Results

✅ **Good Images:**
- Clear, well-lit photos
- Recognizable landmarks
- Single main subject
- High resolution

❌ **Avoid:**
- Blurry or dark photos
- Multiple unrelated subjects
- Low resolution images
- Heavily filtered photos

## Demo Video

These images are featured in our demo video showing the complete image-to-booking flow.

---

**Note:** These are sample images for demonstration purposes. In production, tourists would upload their own photos of places they want to visit.
