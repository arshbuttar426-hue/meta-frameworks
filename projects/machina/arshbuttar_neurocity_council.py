import ollama
import time

class NeuroCityCouncil:
    def __init__(self):
        # The 7 Models from your local M5 registry
        self.agents = {
            "scout":        "qwen2:0.5b",         # Fast, lightweight summarization
            "theorist":     "deepseek-r1:1.5b",   # Deep reasoning and logic
            "archeologist": "phi3.5:latest",      # Physics and hardware constraints
            "lead_coder":   "qwen2.5-coder:3b",   # Core script generation
            "junior_coder": "qwen2.5-coder:1.5b", # Code syntax and optimization
            "critic":       "gemma4:e2b",         # Peer review (using exact ID from your list)
            "architect":    "gemma2:9b"           # The Heavyweight Lead: Final Verdict
        }

    def trigger_agent(self, role, task, context=""):
        model_name = self.agents.get(role)
        if not model_name:
            return f"Error: Agent '{role}' not found."

        print(f"\n[{role.upper()}] ({model_name}) is processing...")
        start_time = time.time()
        
        # Combine the previous context with the new task
        full_prompt = f"Previous Context:\n{context}\n\nYour Task:\n{task}" if context else task
        
        try:
            response = ollama.generate(model=model_name, prompt=full_prompt)
            output = response['response']
            print(f" -> Completed in {round(time.time() - start_time, 2)} seconds")
            return output
        except Exception as e:
            return f"Model Failed: {e}"

# ==========================================
# EXECUTION PIPELINE
# ==========================================
if __name__ == "__main__":
    council = NeuroCityCouncil()
    
    print("🟢 NEUROCITY COUNCIL INITIATED - ALL 7 AGENTS ONLINE\n")
    
    # The Core Problem
    core_problem = "QnA - Can a thumb's average reach on a phone screen over time allow us to know their height?"
    print(f"MISSION: {core_problem}")
    print("-" * 50)

    # Step 1: The Scout summarizes the raw mission into a technical spec
    spec = council.trigger_agent("scout", "Turn this mission into a 2-sentence technical objective.", core_problem)
    
    # Step 2: The Theorist expands the physics
    theory = council.trigger_agent("theorist", "Explain the theoretical physics of this objective. How would the waves interact?", spec)
    
    # Step 3: The Archeologist applies hardware reality
    hardware = council.trigger_agent("archeologist", "Audit this theory for hardware reality. What are the limits of a 48kHz sample rate here?", theory)
    
    # Step 4: The Lead Coder drafts a simulation script
    code_draft = council.trigger_agent("lead_coder", "Write a Python simulation to test these hardware limits using NumPy.", hardware)
    
    # Step 5: The Junior Coder optimizes it
    optimized_code = council.trigger_agent("junior_coder", "Review this Python code. Fix any bugs and optimize it for Apple Silicon (Metal/MPS) if possible.", code_draft)
    
    # Step 6: The Critic reviews the entire flow
    review = council.trigger_agent("critic", "Review the physics theory and the code. Identify one major flaw.", theory + "\n" + optimized_code)
    
    # Step 7: The Architect (Heaviest Model) gives the Final Verdict
    architect_prompt = "You are the Lead Architect. Review the critic's flaw and the hardware constraints. Give a final GO or NO-GO for this project with a 1-paragraph justification."
    verdict = council.trigger_agent("architect", architect_prompt, hardware + "\n" + review)

    print("\n" + "=" * 50)
    print("🏛️ ARCHITECT'S FINAL VERDICT 🏛️")
    print("=" * 50)
    print(verdict)
