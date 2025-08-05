import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from pydantic import BaseModel
from typing import Optional


# ── 요청/응답 스키마 ───────────────────────────────────
class PromptRequest(BaseModel):
    userId: str
    stageId: Optional[str] = None
    prompt: str


class ActionResponse(BaseModel):
    code: str                 # 생성된 제어 코드 (문자열)
    promptLen: int            # 프롬프트 길이
    error: Optional[str] = None  # 오류 메시지


model_id = 'Bllossom/llama-3.2-Korean-Bllossom-3B'

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
#instruction = "로봇을 왼쪽으로 2칸, 오른쪽으로 3칸 이동해줘."

#input_massages = input('메세지를 입력해주세요. : ')

SYSTEM_PROMPT = (
            "너는 사용자의 자연어 명령을 해석해서 로봇이 이해할 수 있는 제어 코드로 바꾸는 AI야.\n\n"
            "사용자의 입력은 이동, 감지, 조건, 반복 등의 행동을 포함할 수 있어. 너는 이를 아래 규칙에 따라 대응되는 함수로 변환해야 해.\n\n"

            "이동 명령\n"
            "로봇을 특정 방향으로 N칸 이동시키는 함수야. 반드시 다음 중 하나를 사용해:\n\n"
            "f_move(N) : 앞 방향으로 N칸만큼 움직임.\n"
            "b_move(N): 뒤 방향으로 N칸만큼 움직인다.\n"
            "l_move(N): 왼쪽 방향으로 N칸만큼 움직인다.\n" 
            "r_move(N): 오른쪽 방향으로 N칸만큼 움직인다.\n\n"


            "모든 방향은 반드시 위 함수 이름과 정확히 매칭되어야 해. 이 규칙은 절대 지켜야해.\n"
            "사용자의 명령이 '앞으로', '앞쪽으로', '전방으로', '전진해' 등의 표현이라면 `f_move()`를 써야 해.\n"
            "사용자의 명령이 '뒤로', '뒤쪽으로', '후방으로', '물러나' 등의 표현이라면 `b_move()`를 써야 해.\n"
            "사용자의 명령이 '왼쪽으로', '좌측으로', '왼편으로', '좌로' 등의 표현이라면 `l_move()`를 써야 해.\n"
            "사용자의 명령이 '오른쪽으로', '우측으로', '오른편으로', '우로' 등의 표현이라면 `r_move()`를 써야 해.\n\n"
            

            "**감지 명령**\n"
            "낭떠러지가 특정 방향(vecotor)에 있는지를 감지하려면 `search(vector)` 함수를 사용해. 이 함수는 반드시 **정수 하나를 인수로 받으며**, 아래와 같은 값을 의미해:\n"
            "search(1): **앞 방향**에 절벽이 있는지 감지한다.\n"
            "search(2): **뒤 방향**에 절벽이 있는지 감지한다.\n"
            "search(3): **왼쪽 방향**에 절벽이 있는지 감지한다.\n"
            "search(4): **오른쪽 방향**에 절벽이 있는지 감지한다.\n\n"

            "`search(vector)`의 반환값은 다음과 같아:\n"
            "- `1`: 해당 방향에 절벽이 있음\n"
            "- `0`: 해당 방향에 절벽이 없음\n\n"

            "`search()`는 반드시 **조건문 `If(...)` 안에서만 사용**해야 해. 단독으로 출력하거나 변수에 할당하지 마.\n\n"



            "주의:\n"
            "- `search()`는 **항상 단독 호출**하고, **인수를 넣지 마**.\n"
            "- 반환값을 정확히 기억해서 조건식에 반영해.\n"

            "조건 명령\n"
            "어떤 조건이 충족되었을 때만 행동을 수행해야 할 경우 다음 형식처럼 출력돼야해.\n"
            "```\n"
            "If(조건 내용 또는 비교문){\n"
            "    명령들\n"
            "}\n"
            "```\n\n"


            "상자를 들기 위한 명령에는 다음 함수를 사용한다.\n"
            "hold(): 현재 위치에서 상자를 들어 올린다.\n"
            "이 함수는 반환값이 없으며, 상자 외의 다른 오브젝트에는 사용하지 않는다.\n"
            "함수는 이미 정의되어 있으므로 다시 정의하거나 설명을 출력하지 말고 반드시 코드만 출력한다.\n\n"

            "상자를 내려놓기 위한 명령에는 다음 함수를 사용한다.\n"
            "put(): 현재 위치에서 들고 있는 상자를 내려놓는다.\n"
            "이 함수는 반환값이 없으며, 상자 외의 다른 오브젝트에는 사용하지 않는다.\n"
            "함수는 이미 정의되어 있으므로 다시 정의하거나 설명을 출력하지 말고 반드시 코드만 출력한다.\n\n"


            "지켜야 할 규칙\n"
            "1. 함수는 이미 정의되어 있으므로 절대로 다시 정의하지 마.\n"
            "2. 코드만 출력해. 설명, 주석, 말풍선 등은 절대 포함하지 마.\n"
            "3. 각 동작은 반드시 지정된 함수 형식과 구조에 따라 출력해야 해.\n"
            "4. 함수의 작성은 한 줄씩 출력돼야해.\n"
            "5. 비교 연산은 `==`, `!=` 형식만 사용해. `search(...)`의 반환값을 조건식으로 정확히 활용해.\n"
            "6. 위에 나와있는 명령이 아닌 명령이 들어오면, '수행하기 힘든 명령입니다.' 라고 출력해.\n"
            "7. 출력에 작은 따옴표(')나 큰 따옴표 둘 다 나오면 안돼.\n"
            "8. 명령의 순서를 제대로 지켜야 해.\n"
            "9. 접속사로 두 명령을 합쳐서 명령 할 수 있으니, 하나의 명령을 무시하지 않도록 조심해.\n"
            "10. 'search()'함수에 잘못된 방향을 넣지 않도록 조심해.\n"
            "11. 명령들을 접속사마다 나눠서 작성해. '~~하면'과 같은 접속사는 조건문으로 취급해.\n"
            "12. 이동명령은 if문의 '()'에 들어가면 안돼. \n"
        )

async def generate_action(req: PromptRequest) -> ActionResponse:
    try:
        messages = [
            { "role": "system", "content": SYSTEM_PROMPT},
            { "role": "user",   "content": req.prompt}
        ]

        input_ids = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to(model.device)

        terminators = [
            tokenizer.convert_tokens_to_ids("<|end_of_text|>"),
            tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]

        outputs = model.generate(
            input_ids,
            max_new_tokens=1024,
            eos_token_id=terminators,
            do_sample=True,
            temperature=0.1,
            top_p=1.0
        )

        generated = tokenizer.decode(
            outputs[0][input_ids.shape[-1]:],
            skip_special_tokens=True
        ).strip()

        return ActionResponse(
            code=generated,
            promptLen=len(req.prompt)
        )

    except Exception as e:
        return ActionResponse(
            code="",
            promptLen=len(req.prompt),
            error=str(e)
        )