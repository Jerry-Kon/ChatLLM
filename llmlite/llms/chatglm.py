from typing import List, Optional, Tuple, Dict, Any
import logging

from transformers import AutoTokenizer  # type: ignore

from llmlite.llms.model import Model
from llmlite.utils.util import get_class
from llmlite.llms.messages import ChatMessage
from llmlite import consts
from llmlite.utils import util

chatglm2 = 2
chatglm3 = 3


class ChatGLM(Model):
    """
    ChatGLM is mainly used for chinese questions and answers. Currently don't support system prompt yet.
    """

    def __init__(self, model_name_or_path: str, **kwargs: Dict[str, Any]) -> None:
        super().__init__(model_name_or_path, **kwargs)

    __config__ = {
        "support_system_prompt": False,
        "backends": [consts.BACKEND_HF, consts.BACKEND_VLLM],
        "default_backend": consts.BACKEND_HF,
        "architecture": "AutoModel",
    }

    @classmethod
    def load_with_hf(
        cls,
        model_name_or_path: str,
        **kwargs: Dict[str, Any],
    ):
        trust_remote_code = kwargs.pop("trust_remote_code", True)

        arch = cls.__config__.get("architecture", None)
        if arch is None:
            raise Exception("architecture not exists")

        model_class = get_class("transformers", arch)

        tokenizer = AutoTokenizer.from_pretrained(
            model_name_or_path,
            trust_remote_code=trust_remote_code,
        )
        model = (
            model_class.from_pretrained(
                model_name_or_path,
                trust_remote_code=trust_remote_code,
                **kwargs,
            )
            .half()
            .cuda()
            .eval()
        )

        config_args = {
            "backend": consts.BACKEND_HF,
            "tokenizer": tokenizer,
            "model": model,
            "logger": logging.getLogger("llmlite.ChatGLM"),
        }
        return cls(model_name_or_path, **config_args)

    def completion(
        self,
        messages: List[ChatMessage],
        **kwargs,
    ) -> Optional[str]:
        """
        This is how ChatGLM chat() looks like:

        def chat(
            self,
            tokenizer,
            query: str,
            history: List[Tuple[str, str]] = None,
            max_length: int = 8192,
            num_beams=1,
            do_sample=True,
            top_p=0.8,
            temperature=0.8,
            logits_processor=None,
            **kwargs,
            )
        """

        if self.version == chatglm2 and self.backend == consts.BACKEND_HF:
            query, history = build_history(messages)
            response, _ = self.model.chat(
                self.tokenizer,
                query,
                history=history,
            )
            return response

        # TODO: support vllm
        if self.version == chatglm2 and self.backend == consts.BACKEND_VLLM:
            pass

        # TODO: support chatglm3
        if self.version == chatglm3 and self.backend == consts.BACKEND_HF:
            pass
        if self.version == chatglm3 and self.backend == consts.BACKEND_VLLM:
            pass

    @classmethod
    def prompt(
        cls,
        model_name_or_path: str,
        messages: List[ChatMessage],
        **kwargs,
    ) -> Optional[str]:
        super().prompt(model_name_or_path, messages, **kwargs)

        _, version = util.parse_model_name(model_name_or_path)

        # TODO: how vllm support conversion chatglm.
        if version == chatglm2:
            prompt = ""
            query, history = build_history(messages)

            # This is inspired by /root/.cache/huggingface/modules/transformers_modules/chatglm2-6b/tokenization_chatglm.py::build_prompt().
            for i, (old_query, response) in enumerate(history):
                prompt += "[Round {}]\n\n问：{}\n\n答：{}\n\n".format(
                    i + 1, old_query, response
                )
            prompt += "[Round {}]\n\n问：{}\n\n答：".format(len(history) + 1, query)
            return prompt

        # TODO: support chatglm3
        if version == chatglm3:
            return None


def build_history(messages: List[ChatMessage]) -> Tuple[str, List[Tuple[str, str]]]:
    query = messages[-1].content
    history = []

    pair_number = int(len(messages) / 2)
    for i in range(0, pair_number):
        history.append((messages[2 * i].content, messages[2 * i + 1].content))

    return query, history
