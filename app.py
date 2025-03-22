# app.py
import streamlit as st
import os
from datetime import datetime
import tempfile
from dotenv import load_dotenv
from services.ai_service import OpenAIService
from services.storage_service import StorageService
from services.wine_service import WineService
from utils.helpers import process_uploaded_image, format_wine_list

# Load environment variables
load_dotenv()

# Initialize services
ai_service = OpenAIService()
storage_service = StorageService()
wine_service = WineService()

# Password protection
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == os.getenv("APP_PASSWORD"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store the password
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated
    if "password_correct" in st.session_state:
        return st.session_state["password_correct"]
    
    # First run, show input for password
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    return False

# Set page config
st.set_page_config(page_title="Carlos Wine Assistant", page_icon="🍷", layout="wide")

# Check password
if not check_password():
    st.error("Please enter the correct password to access the Wine Assistant.")
    st.stop()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_mode" not in st.session_state:
    st.session_state.conversation_mode = "general"
if "storage_configured" not in st.session_state:
    st.session_state.storage_configured = storage_service.has_storage()
if "temp_wine" not in st.session_state:
    st.session_state.temp_wine = None
if "temp_position" not in st.session_state:
    st.session_state.temp_position = None

# App header
st.title("🍷 Carlos Wine Assistant")

# Sidebar with stats and actions
with st.sidebar:
    st.header("Collection Stats")
    wines = wine_service.get_wines()
    st.write(f"Total wines: {len(wines)}")
    
    # Display a few wines if available
    if wines:
        st.subheader("Recent Wines")
        for wine in wines[:5]:
            st.write(f"• {wine['name']}")
    
    # Action buttons
    st.subheader("Actions")
    
    # Add Wine button
    if st.button("Add Wine"):
        st.session_state.conversation_mode = "wine_add"
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Let's add a new wine to your collection. Please upload a picture of the wine label."
        })
        st.rerun()
    
    # Find Pairing button
    if st.button("Find Pairing"):
        st.session_state.conversation_mode = "pairing"
        st.session_state.messages.append({
            "role": "assistant",
            "content": "What are you eating? You can describe the dish or upload a photo of it."
        })
        st.rerun()
    
    # Set Up Storage button (only if not configured)
    if not st.session_state.storage_configured and st.button("Set Up Storage"):
        st.session_state.conversation_mode = "storage_setup"
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Let's set up your wine storage. Please describe your wine storage setup in detail (type, size, zones, temperature control, etc.)"
        })
        st.rerun()

if st.sidebar.button("View Storage Positions"):
    # Instead of setting a flag, add a message to the conversation
    import sqlite3
    import pandas as pd
    
    conn = sqlite3.connect("wine_collection.db")
    conn.row_factory = sqlite3.Row
    
    # Get storage info
    storage = conn.execute("SELECT * FROM storage").fetchone()
    
    if storage:
        # Get all positions with wine information
        positions = conn.execute("""
            SELECT p.id, p.zone, p.identifier, p.is_occupied, 
                   w.id as wine_id, w.name as wine_name 
            FROM positions p
            LEFT JOIN wines w ON p.wine_id = w.id AND w.consumed = 0
            ORDER BY p.zone, p.identifier
        """).fetchall()
        
        # Group by zone
        zones = {}
        for pos in positions:
            zone = pos["zone"]
            if zone not in zones:
                zones[zone] = []
            zones[zone].append(pos)
        
        # Create a formatted message
        message = f"## Storage: {storage['description'][:50]}...\n\n"
        
        for zone, zone_positions in zones.items():
            message += f"### Zone: {zone}\n\n"
            message += "| Position | Status | Wine |\n"
            message += "| --- | --- | --- |\n"
            
            for pos in zone_positions:
                status = "Occupied" if pos["is_occupied"] else "Empty"
                wine = pos["wine_name"] if pos["wine_name"] else "None"
                message += f"| {pos['identifier']} | {status} | {wine} |\n"
            
            message += "\n"
        
        # Add the message to the chat
        st.session_state.messages.append({
            "role": "assistant",
            "content": message
        })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "No storage configuration found. Please set up your storage first."
        })
    
    conn.close()
    st.rerun()

# Display chat messages
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# File uploader (conditionally displayed based on conversation mode)
if st.session_state.conversation_mode in ["wine_add", "pairing"]:
    upload_text = "Upload a wine label image" if st.session_state.conversation_mode == "wine_add" else "Upload a food image"
    uploaded_file = st.file_uploader(
        upload_text, 
        type=["jpg", "jpeg", "png"],
        key=f"uploader_{st.session_state.conversation_mode}"
    )
    
    if uploaded_file:
        image_data = uploaded_file.getvalue()
        # Display image with controlled width instead of full container width
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(image_data, caption="Uploaded Image", width=300)
        
        # Process image based on mode
        if st.session_state.conversation_mode == "wine_add":
            with st.spinner("Analyzing wine label..."):
                result = ai_service.analyze_wine_label(image_data)
                
                if result["success"]:
                    wine_data = result["data"]
                    st.session_state.temp_wine = {
                        "name": wine_data["name"],
                        "description": wine_data["description"]
                    }
                    
                    # Show wine details for confirmation
                    st.subheader("Wine Details")
                    st.write(f"**Name:** {wine_data['name']}")
                    st.write(f"**Description:** {wine_data['description']}")
                    
                    # Suggest position based on wine type
                    positions = storage_service.get_available_positions()
                    if positions:
                        # Determine if it's a white or red wine
                        is_white_wine = False
                        if isinstance(wine_data['description'], dict):
                            wine_type = wine_data['description'].get('wine_type', '').lower()
                            is_white_wine = 'white' in wine_type or 'blanc' in wine_type
                        else:
                            # Try to infer from the description text
                            description_lower = wine_data['description'].lower()
                            is_white_wine = 'white' in description_lower or 'blanc' in description_lower
                        
                        # Find appropriate position based on wine type
                        appropriate_positions = []
                        for pos in positions:
                            # White wines go to first zone (contains "White" in zone name)
                            if is_white_wine and "White" in pos["zone"]:
                                appropriate_positions.append(pos)
                            # Red wines go to second zone (contains "Red" in zone name)
                            elif not is_white_wine and "Red" in pos["zone"]:
                                appropriate_positions.append(pos)
                        
                        # If no appropriate positions found, fall back to any available position
                        if not appropriate_positions:
                            appropriate_positions = positions
                        
                        position = appropriate_positions[0]
                        st.session_state.temp_position = position
                        
                        wine_type_str = "white" if is_white_wine else "red"
                        st.write(f"**Suggested Position:** {position['identifier']} ({position['zone']})")
                        st.write(f"*Recommendation based on {wine_type_str} wine type.*")
                        
                        if st.button("Confirm and Add to Collection"):
                            # Save wine to database with position
                            wine_data = st.session_state.temp_wine
                            wine_data["position_id"] = position["id"]
                            wine_service.add_wine(wine_data)
                            
                            # Add confirmation message
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"I've added {wine_data['name']} to your collection at position {position['identifier']}. Is there anything else you'd like to do?"
                            })
                            
                            # Reset session values
                            st.session_state.temp_wine = None
                            st.session_state.temp_position = None
                            st.session_state.conversation_mode = "general"
                            
                            # Clear file uploader by creating a new key
                            st.rerun()
                    else:
                        st.error("No available positions in your storage. Please free up space by consuming wines.")
                else:
                    st.error(f"Could not analyze wine label: {result.get('error', 'Unknown error')}. Please try again.")
        
        elif st.session_state.conversation_mode == "pairing":
            with st.spinner("Analyzing food image..."):
                wines = wine_service.get_wines()
                if not wines:
                    st.warning("Your collection is empty. Add some wines first!")
                else:
                    wine_list = [{"name": wine["name"], "description": wine["description"]} for wine in wines]
                    result = ai_service.get_pairing_recommendation(image_data, wine_list, is_image=True)
                    
                    if result["success"]:
                        recommendation = result["recommendation"]
                        
                        # Show recommendation
                        st.subheader("Wine Pairing Recommendation")
                        st.write(recommendation)
                        
                        # Add to chat
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": recommendation
                        })
                        st.session_state.conversation_mode = "general"
                        st.rerun()
                    else:
                        st.error(f"Could not analyze food image: {result.get('error', 'Unknown error')}. Please try again or describe the dish instead.")

# Chat input for text conversation
user_input = st.chat_input("Ask about your wine collection...")
if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Handle based on conversation mode
    if st.session_state.conversation_mode == "storage_setup":
        with st.spinner("Processing your storage description..."):
            # Process storage setup description
            result = ai_service.get_storage_configuration(user_input)
            
            if result["success"]:
                storage_data = result["data"]
                storage_service.create_storage(storage_data)
                st.session_state.storage_configured = True
                
                # Add assistant message
                zone_info = ", ".join([zone["name"] for zone in storage_data["zones"]])
                positions_count = storage_data["total_positions"]
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"I've set up your storage based on your description. You now have {positions_count} positions available across these zones: {zone_info}. You can start adding wines to your collection."
                })
                st.session_state.conversation_mode = "general"
                st.rerun()
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"I couldn't process your storage description: {result.get('error', 'Unknown error')}. Please try again with more details about your storage setup."
                })
                st.rerun()
    
    elif st.session_state.conversation_mode == "pairing":
        with st.spinner("Finding the perfect pairing..."):
            wines = wine_service.get_wines()
            if not wines:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Your collection is empty. Add some wines first before I can recommend pairings."
                })
                st.session_state.conversation_mode = "general"
                st.rerun()
            else:
                wine_list = [{"name": wine["name"], "description": wine["description"]} for wine in wines]
                result = ai_service.get_pairing_recommendation(user_input, wine_list, is_image=False)
                
                if result["success"]:
                    recommendation = result["recommendation"]
                    
                    # Add assistant message
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": recommendation
                    })
                    st.session_state.conversation_mode = "general"
                    st.rerun()
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"I couldn't generate a recommendation: {result.get('error', 'Unknown error')}. Please try again."
                    })
                    st.rerun()
    
    elif st.session_state.conversation_mode == "general":
        # Process general queries
        lower_input = user_input.lower()
        
        if "consumed" in lower_input or "finished" in lower_input or "drank" in lower_input or "emptied" in lower_input:
            # Handle marking a wine as consumed
            wines = wine_service.get_wines()
            if not wines:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "You don't have any wines in your collection to mark as consumed."
                })
                st.rerun()
            else:
                st.session_state.conversation_mode = "mark_consumed"
                
                wine_names = [f"{i+1}. {wine['name']}" for i, wine in enumerate(wines)]
                wines_list = "\n".join(wine_names)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Which wine have you consumed? Please specify by number or name:\n\n{wines_list}"
                })
                st.rerun()
        
        elif "collection" in lower_input or "inventory" in lower_input or "wines" in lower_input:
            # Handle collection status
            wines = wine_service.get_wines()
            if wines:
                collection_text = format_wine_list(wines)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Here's your current wine collection:\n\n{collection_text}"
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Your collection is currently empty. You can add wines by uploading pictures of wine labels."
                })
            st.rerun()
        
        elif "add" in lower_input and ("wine" in lower_input or "bottle" in lower_input):
            # Switch to wine add mode
            st.session_state.conversation_mode = "wine_add"
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Let's add a new wine to your collection. Please upload a picture of the wine label."
            })
            st.rerun()
        
        elif "pairing" in lower_input or "pair" in lower_input or ("recommend" in lower_input and "food" in lower_input):
            # Switch to pairing mode
            st.session_state.conversation_mode = "pairing"
            st.session_state.messages.append({
                "role": "assistant",
                "content": "What are you eating? You can describe the dish or upload a photo of it."
            })
            st.rerun()
        
        elif "storage" in lower_input or "positions" in lower_input or "fridge" in lower_input:
            # Handle storage view within chat
            import sqlite3
            
            conn = sqlite3.connect("wine_collection.db")
            conn.row_factory = sqlite3.Row
            
            # Get storage info
            storage = conn.execute("SELECT * FROM storage").fetchone()
            
            if storage:
                # Get all positions with wine information
                positions = conn.execute("""
                    SELECT p.id, p.zone, p.identifier, p.is_occupied, 
                           w.id as wine_id, w.name as wine_name 
                    FROM positions p
                    LEFT JOIN wines w ON p.wine_id = w.id AND w.consumed = 0
                    ORDER BY p.zone, p.identifier
                """).fetchall()
                
                # Group by zone
                zones = {}
                for pos in positions:
                    zone = pos["zone"]
                    if zone not in zones:
                        zones[zone] = []
                    zones[zone].append(pos)
                
                # Create a formatted message
                message = f"## Storage: {storage['description'][:50]}...\n\n"
                
                for zone, zone_positions in zones.items():
                    message += f"### Zone: {zone}\n\n"
                    message += "| Position | Status | Wine |\n"
                    message += "| --- | --- | --- |\n"
                    
                    for pos in zone_positions:
                        status = "Occupied" if pos["is_occupied"] else "Empty"
                        wine = pos["wine_name"] if pos["wine_name"] else "None"
                        message += f"| {pos['identifier']} | {status} | {wine} |\n"
                    
                    message += "\n"
                
                # Add the message to the chat
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": message
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "No storage configuration found. Please set up your storage first."
                })
            
            conn.close()
            st.rerun()
        
        else:
            # Handle with GPT-4o for general wine-related queries
            with st.spinner("Thinking..."):
                # Build context about the user's collection
                wines = wine_service.get_wines()
                storage_configured = storage_service.has_storage()
                
                collection_context = ""
                if wines:
                    collection_context = f"The user has {len(wines)} wines in their collection."
                else:
                    collection_context = "The user's collection is currently empty."
                
                if not storage_configured:
                    collection_context += " The user has not set up their storage yet."
                
                # Create a message for AI
                messages = [
                    {
                        "role": "system",
                        "content": f"You are a wine assistant helping with a personal wine collection. {collection_context} Provide helpful, concise responses. If the query needs functionality like adding wines, checking the collection, or finding pairings, suggest using the appropriate buttons or commands."
                    },
                    {
                        "role": "user",
                        "content": user_input
                    }
                ]
                
                response = ai_service.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=800
                )
                
                assistant_response = response.choices[0].message.content
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })
                st.rerun()
    
    elif st.session_state.conversation_mode == "mark_consumed":
        # Handle the wine consumption marking
        wines = wine_service.get_wines()
        
        # Try to find the wine by number or name
        selected_wine = None
        
        # Check if user entered a number
        try:
            wine_num = int(user_input.strip())
            if 1 <= wine_num <= len(wines):
                selected_wine = wines[wine_num - 1]
        except ValueError:
            # Not a number, try to find by name
            user_input_lower = user_input.lower()
            for wine in wines:
                if user_input_lower in wine["name"].lower():
                    selected_wine = wine
                    break
        
        if selected_wine:
            # Mark wine as consumed
            wine_service.mark_wine_consumed(selected_wine["id"])
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I've marked '{selected_wine['name']}' as consumed and freed up its position in your storage. Enjoy!"
            })
            st.session_state.conversation_mode = "general"
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "I couldn't find that wine in your collection. Please try again with the exact name or number from the list."
            })
        
        st.rerun()

# Initial greeting (only on first load)
if len(st.session_state.messages) == 0:
    greeting = "👋 Welcome to Carlos Wine Assistant! I can help you organize your wine collection and find perfect pairings."
    
    if not st.session_state.storage_configured:
        greeting += " Let's start by setting up your wine storage. Click the 'Set Up Storage' button in the sidebar to begin."
    else:
        greeting += " You can add wines, find pairings, or check your collection using the buttons in the sidebar."
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": greeting
    })
    st.rerun()