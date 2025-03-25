import regex as re


class SplitText:
    def __init__(self) -> None:
        self.quote_pairs = {'"': '"', "'": "'", "‘": "’", "“": "”"}
        self.bracket_pairs = {
            "(": ")",
            "（": "）",
            "[": "]",
            "【": "】",
            "{": "}",
            "《": "》",
            "「": "」",
            "『": "』",
        }
        self.all_pairs = {**self.quote_pairs, **self.bracket_pairs}
        self.reverse_pairs = {v: k for k, v in self.all_pairs.items()}

        self.must_terminate_punc = [
            "。",
            "!",
            "！",
            "?",
            "？",
            "……",
            "\n",
        ]  # 长度为 1 或 2 的 str，因为 …… 有两个字符
        self.terminate_punc = [
            "」",
            "』",
            "；",
            ";",
        ]
        self.intermidiate_punc = [",", "，", "…", "）"]

        self.pair_stack = []
        self.current: str = ""
        self.segments: list[str] = []
        self.max_length = 17

    def pair_stack_depth(self) -> int:
        return len(self.pair_stack)

    def update_pair_stack(self, char: str) -> None | int:
        if char in self.all_pairs:
            self.pair_stack.append(char)
            return None
        elif char in self.reverse_pairs:
            target = self.reverse_pairs[char]
            # 从栈顶开始反向查找匹配的开启符号
            for i in reversed(range(len(self.pair_stack))):
                if self.pair_stack[i] == target:
                    # 删除匹配项及其之后的所有元素
                    deleted = self.pair_stack[i:]
                    del self.pair_stack[i:]
                    return len(deleted)
            return None
        else:
            return None

    def clear_pair_stack(self) -> None:
        self.pair_stack.clear()

    def is_punctuation(self, char) -> bool:
        re_is_punctuation = r"[\p{P}\p{S}]"  # 判断是不是标点符号和货币的正则
        return re.match(re_is_punctuation, char) is not None

    def mv_current_to_segment(self) -> None:
        res = self.current.strip()
        if res != "":
            self.segments.append(res)
        self.current = ""
        self.clear_pair_stack()

    def commit_break(self, ch: str) -> None:
        if ch not in [",", "，", "。", ";"]:
            self.current = self.current + ch
        self.mv_current_to_segment()

    def split(self, text: str) -> list[str]:
        """
        0.  (最高优先级) Must Break
        1. （最高优先级）连续的标点符号一定不可被分割
        2. （最高优先级）括号对、引号对里的文字不可分割
        3. （普通优先级） 视字数分割：逗号、省略号、出现时，可能被分割，如果该句大于17个字，则分割
        4. （普通优先级）分句：感叹号、句号、右括号、右引号被分割，除非后续还是标点符号（也就是连续的标点符号不可分割）
        5. （最低优先级）连续的标点符号长度大于3，则在最后一个标点符号进行 视字数分割，也就是看此句是否大于17个字
        6. （提交时处理）prune: 逗号、句号被分割时，自身不保留

        效果：
        - 颜文字可能单独分割，也可能出现在句尾
        - 用英文句号模拟的省略号会在一定长度后被分割
        -
        """
        if len(text) == 0:
            return []
        if len(text) == 1:
            return [text]

        # current seg state
        continuous_count = 0
        count_of_pairs_per_seg = 0

        def rest_current_seg_state():
            nonlocal continuous_count
            continuous_count = 0
            nonlocal count_of_pairs_per_seg
            count_of_pairs_per_seg = 0

        for i in range(len(text) - 1):
            j = i + 1

            char_i = text[i]  # 当前分割字符
            char_j = text[j]

            must_continue = False
            must_terminate = False
            is_continuous = False
            is_in_quote_or_bracket = False
            intermediate_split = False
            regular_split = False
            commit_last = False

            # stage: update rule markers
            if char_j in self.must_terminate_punc:
                must_continue = True
            elif char_i in self.must_terminate_punc:
                must_terminate = True
            if i - 1 >= 0 and text[i - 1] + char_i in self.must_terminate_punc:
                must_terminate = True

            if (
                char_i in self.all_pairs
                and count_of_pairs_per_seg > 0
                and (
                    self.all_pairs[char_i] in self.must_terminate_punc
                    or self.all_pairs[char_i] in self.terminate_punc
                    or self.all_pairs[char_i] in self.intermidiate_punc
                )
            ):
                commit_last = True  # 一句话只出现一个括号对
                rest_current_seg_state()

            if self.update_pair_stack(char_i):
                count_of_pairs_per_seg += 1
            if self.pair_stack_depth() > 0:
                is_in_quote_or_bracket = True
            if self.is_punctuation(char_i) and self.is_punctuation(char_j):
                is_continuous = True
                continuous_count += 1
            elif continuous_count > 3:
                intermediate_split = True
            if char_i in self.intermidiate_punc:
                intermediate_split = True
            if char_i in self.terminate_punc:
                regular_split = True

            # stage: exe rules
            if must_continue:
                self.current += char_i
            elif must_terminate and not is_in_quote_or_bracket:
                self.commit_break(char_i)
                rest_current_seg_state()
            elif is_continuous or is_in_quote_or_bracket:
                if commit_last:
                    self.mv_current_to_segment()
                self.current += char_i  # don't split
            elif commit_last:
                self.mv_current_to_segment()
                self.current += char_i

            elif intermediate_split:
                if len(self.current) > self.max_length:
                    if continuous_count >= 3:  # 连续的标点符号，可能是... 或颜文字
                        # 这里其实不该涉及状态改变但懒得再加一条细分规则变量了
                        continuous_count = 0
                        self.current += char_i
                        self.mv_current_to_segment()
                        rest_current_seg_state()
                    else:
                        self.commit_break(char_i)
                        rest_current_seg_state()
                else:
                    self.current += char_i  # don't split
            elif regular_split:
                self.commit_break(char_i)
                rest_current_seg_state()

            else:
                self.current += char_i  # don't split

        # 最后一个字符无论如何都不分割
        self.commit_break(text[i + 1])

        result = self.segments.copy()
        self.segments.clear()

        return result

    def simple_split(self, text: str, sep: list[str] = ["\n"]) -> list[str]:
        """只依赖换行符的分段"""
        if not sep:
            return [text.rstrip("。")]
        pattern = "|".join([re.escape(s) for s in sep])
        segments = re.split(pattern, text)

        stripped_segments = [
            segment.rstrip("。").rstrip("，").strip() for segment in segments
        ]
        return [s for s in stripped_segments if s]


if __name__ == "__main__":
    split = SplitText()
    test_text = "你好！（兴奋地说）我今天遇到了一个非常有趣的情况，嘿嘿（^_^）你知道吗……？就是那个…（稍微停顿）我们之前讨论过的项目，突然有了意想不到的进展！这真的是……（微笑）太令人兴奋了！"
    print("\n".join(split.split(test_text)))
    print("\n".join(split.split("嗯.....?")))
    print("\n".join(split.split("嗯……?")))
    print("\n".join(split.split("嗯……( >﹏<。)\n也 也许...")))
