from simple_workflows import *
from simple_tools import *
from workflows_as_tools import *
import streamlit as st
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from simple_tools import *
from streamlit_pdf_viewer import pdf_viewer
import os
from dotenv import load_dotenv


def invoke(state, container):
    supervisor_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    tools = create_tools()
    supervisor = supervisor_prompt_template | supervisor_model.bind_tools(tools)
    tool_executor = ToolExecutor(tools)
    folder_structure = get_folder_structure()
    while True:
        workflow_state = {
            "manager_history": state.chat_history,
            "folder_structure": folder_structure,
        }
        action = supervisor.invoke(workflow_state)
        message = st.session_state.messages[-1]
        if "tool_calls" in action.additional_kwargs:
            with container:
                with st.chat_message(message["role"], avatar=":material/build:"):
                    st.write(
                        "I am currently applying: " + action.tool_calls[-1]["name"]
                    )
                    st.write(
                        "Please be patient, some of the tools take time. Check your terminal for progress."
                    )
                    st.session_state.messages.append(
                        {
                            "role": "tool",
                            "content": "Please be patient, some of the tools take time. Check your terminal for progress.",
                        }
                    )
                    st.session_state.messages.append(
                        {
                            "role": "tool",
                            "content": "I am currently using the following tool: "
                            + action.tool_calls[-1]["name"],
                        }
                    )
                    st.session_state.chat_history.append(action)
                    tool_call = action.tool_calls[-1]
                    st.write(tool_call["name"], tool_call["args"])
                    st.session_state.messages.append(
                        {
                            "role": "tool",
                            "content": str(tool_call["name"]) + str(tool_call["args"]),
                        }
                    )
                    Invocation = ToolInvocation(
                        tool=tool_call["name"], tool_input=tool_call["args"]
                    )
                    try:
                        response = tool_executor.invoke(Invocation)
                    except Exception as e:
                        response = str(e)
                    if response is None:
                        response = "Something went wrong"
                    st.write(response)
                    st.session_state.messages.append(
                        {"role": "tool", "content": str(response)}
                    )
                    response = ToolMessage(
                        content=response, tool_call_id=tool_call["id"]
                    )
                    st.session_state.chat_history.append(response)

        if "tool_calls" not in action.additional_kwargs:
            with container:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
            st.session_state.chat_history.append(action)
            st.session_state.messages.append(
                {"role": "assistant", "content": action.content}
            )
            break
    return


def main():
    st.set_page_config(
        page_title="Chat with bot that broke academia! HERE HERE", layout="wide"
    )
    # Streamlit page configuration
    st.markdown(
        "<h1 style='text-align: center;margin-left: -550px;'>Chat with the Bot that broke Academia!!</h1>",
        unsafe_allow_html=True,
    )
    ready = True
    global st_file
    st_file = None
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        st.warning("Missing GEMINI_API_KEY")
        ready = False

    load_dotenv()
    pdfs = "files\\pdfs"
    mmd = "files\\markdowns"

    if "messages" not in st.session_state.keys():
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "I hope you had your morning coffee! Are you ready to get started?",
            }
        ]
    if "awaiting_response" not in st.session_state:
        st.session_state.awaiting_response = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "disable_input" not in st.session_state:
        st.session_state.disable_input = False
    if "st_file" not in st.session_state:
        st.session_state.st_file = None

    # Create a sidebar widget to display the folder structure
    left_sidebar, main_content, right_sidebar = st.columns(
        [0.2, 0.45, 0.35], gap="large"
    )

    # Left sidebar
    with left_sidebar:
        left_container = st.container(height=305)
        with left_container:
            selected_type = st.selectbox(
                "Select a type",
                ["PDF", "Markdown"],
                index=None,
                disabled=st.session_state.disable_input,
            )
            pdf_files = list_files(pdfs)
            markdown_files = list_files(mmd)
            if selected_type == "PDF":
                selected_file = st.selectbox(
                    "Select a file",
                    pdf_files,
                    index=None,
                    disabled=st.session_state.disable_input,
                )
            else:
                selected_file = st.selectbox(
                    "Select a file",
                    markdown_files,
                    index=None,
                    disabled=st.session_state.disable_input,
                )

            if selected_file:
                if selected_type == "PDF":
                    st.session_state.st_file = os.path.join(
                        pdfs, selected_file + ".pdf"
                    )
                else:
                    st.session_state.st_file = os.path.join(mmd, selected_file + ".mmd")

            uploaded_file = st.file_uploader(
                "Import Manually",
                type=["pdf", "mmd"],
                disabled=st.session_state.disable_input,
            )
            # Handle the uploaded file
            if uploaded_file is not None:
                # Save the uploaded file to the specified directory
                _, file_extension = os.path.splitext(uploaded_file.name)
                if file_extension == ".pdf":
                    save_path = os.path.join(pdfs, uploaded_file.name)
                else:
                    save_path = os.path.join(mmd, uploaded_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"File '{uploaded_file.name}' uploaded successfully!")
        st.image("files/images/robot2.png", use_column_width=True)

    with right_sidebar:
        right_container = st.container(height=755)
        with right_container:
            if not gemini_api_key:
                gemini_api_key = "You dont have an GEMINI_API_KEY, get one from here: https://aistudio.google.com/app/apikey, and put it in the .env file"

            if not st.session_state.st_file:
                with open("README.MD", "r") as file:
                    markdown_content = file.read()
                st.markdown(markdown_content)
            elif st.session_state.st_file and selected_type == "PDF":
                pdf_viewer(st.session_state.st_file)
            elif st.session_state.st_file and selected_type == "Markdown":
                with open(st.session_state.st_file, "r", encoding="utf-8") as file:
                    markdown_content = file.read()
                st.markdown(markdown_content)

    # Main content
    if ready:
        with main_content:
            # Chat history container with scrollbar
            chat_container = st.container(height=700)
            with chat_container:
                for message in st.session_state.messages:
                    if message["role"] == "tool":
                        with st.chat_message(
                            message["role"], avatar=":material/build:"
                        ):
                            st.write(message["content"])
                    else:
                        with st.chat_message(message["role"]):
                            st.write(message["content"])

            # Display the input widget with the disabled condition
            prompt = st.chat_input(
                "Enter your querry", disabled=st.session_state.disable_input
            )
            if st.session_state.awaiting_response is False:
                if prompt:
                    st.session_state.messages.append(
                        {"role": "user", "content": prompt}
                    )
                    st.session_state.chat_history.append(HumanMessage(content=prompt))
                    st.session_state.awaiting_response = True
                    with chat_container:
                        with st.chat_message("user"):
                            st.write(prompt)
                            st.session_state.disable_input = True
                    st.rerun()

            # Generate a new response if last message is not from assistant
            if st.session_state.awaiting_response:
                with chat_container:
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking...this may take a while"):
                            st.session_state.awaiting_response = False
                            invoke(st.session_state, chat_container)
                            st.session_state.disable_input = False
                st.rerun()
    else:
        st.stop()


if __name__ == "__main__":
    main()
