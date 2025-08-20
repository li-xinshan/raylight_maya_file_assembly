# -*- coding: utf-8 -*-
"""
BlendShape管理模块（精简版）
- 入口函数：create_precise_blendshapes_between_groups(target_group, driver_group)
- 先选“目标组”（被驱动），再选“驱动组”（作为 shape 源）
- 仅对有效 mesh（intermediate=False）操作，统一使用 transform 创建 blendShape
- 匹配策略：名称优先（忽略命名空间），并以 faces+verts 校验；仅当有候选时创建
- 创建方向：驱动 -> 目标（blendShape 加在目标上）
"""

import re
import maya.cmds as mc


class BlendshapeManager:
    """BlendShape管理器（保留入口：create_precise_blendshapes_between_groups）"""

    def __init__(self):
        pass

    # ========== 入口函数（对外） ==========

    def create_precise_blendshapes_between_groups(self, driver_group, target_group):
        """
        在“目标组”和“驱动组”之间批量创建 blendShape（driver -> target）
        Args:
            target_group (str): 目标组（被驱动，blendShape 加在这里）
            driver_group (str): 驱动组（作为 blend target 源）
        Returns:
            list[str]: 创建的 blendShape 节点名列表
        """
        print("\n=== 创建组间 BlendShape（驱动 -> 目标） ===")
        print("目标组:", target_group)
        print("驱动组:", driver_group)

        if not (mc.objExists(target_group) and mc.objExists(driver_group)):
            mc.warning("❌ 指定的组不存在")
            return []

        print('收集 目标组 meshes...')
        tgt_info = self._build_mesh_info(target_group)
        print('收集 驱动组 meshes...')
        drv_info = self._build_mesh_info(driver_group)

        if not tgt_info or not drv_info:
            print("❌ 组内未找到有效 mesh（需 intermediateObject=False 的 mesh）")
            return []

        # 将驱动组按签名分组：sig=(faces, verts) -> [shape...]
        sig_to_drv = {}
        for s, inf in drv_info.items():
            sig_to_drv.setdefault(inf['sig'], []).append(s)

        created = []
        matched = []
        used_drv_shapes = set()

        print("\n开始匹配并创建 blendShape（驱动 -> 目标）...")
        for t_shape, t_inf in tgt_info.items():
            sig = t_inf['sig']
            t_x = t_inf['xform']
            t_key_nonns = t_inf['shortNoNS']

            # 候选：faces+verts 相同的驱动形状，且未被用过
            candidates = [s for s in sig_to_drv.get(sig, []) if s not in used_drv_shapes]
            if not candidates:
                continue

            drv_best = self._pick_best_candidate(t_key_nonns, candidates, drv_info)
            if not drv_best:
                continue

            d_x = drv_info[drv_best]['xform']
            # 再确认 transform 下有有效 mesh
            t_x_valid = self._get_valid_mesh_transform(t_x)
            d_x_valid = self._get_valid_mesh_transform(d_x)
            if not (t_x_valid and d_x_valid):
                print("  跳过（无有效mesh）:", self._short(d_x), "->", self._short(t_x))
                used_drv_shapes.add(drv_best)
                continue

            # 创建 blendShape：源 d_x_valid，目标 t_x_valid
            try:
                bs_name = 'bs_' + self._no_ns(self._short(t_x_valid))
                blend = mc.blendShape(d_x_valid, t_x_valid, origin='world', name=bs_name)[0]
                self._set_blend_weight(blend, d_x_valid, value=1.0)
                created.append(blend)
                matched.append((t_x_valid, d_x_valid))
                used_drv_shapes.add(drv_best)
                print("  ✅ {} -> {}  faces/verts={}  blend={}".format(
                    self._short(d_x_valid), self._short(t_x_valid), sig, blend
                ))
            except Exception as e:
                print("  ❌ 失败:", self._short(d_x_valid), "->", self._short(t_x_valid), "|", e)
                used_drv_shapes.add(drv_best)

        # 统计输出
        print("\n=== 结果统计 ===")
        print("目标组有效mesh数量:", len(tgt_info))
        print("驱动组有效mesh数量:", len(drv_info))
        print("成功创建blendShape:", len(created))
        if created:
            print("\n创建的blendShape节点:")
            for b in created:
                print("  -", b)

        matched_t = {t for t, _ in matched}
        matched_d = {d for _, d in matched}

        if len(matched_t) < len(tgt_info):
            print("\n未匹配的 目标网格:")
            for s, inf in tgt_info.items():
                if inf['xform'] not in matched_t:
                    print("  - {} (faces/verts={})".format(self._short(inf['xform']), inf['sig']))

        if len(matched_d) < len(drv_info):
            print("\n未匹配的 驱动网格:")
            for s, inf in drv_info.items():
                if inf['xform'] not in matched_d:
                    print("  - {} (faces/verts={})".format(self._short(inf['xform']), inf['sig']))

        return created

    # ========== 内部工具 ==========

    def _short(self, n):
        return n.split('|')[-1]

    def _no_ns(self, n):
        return n.split(':')[-1]

    def _is_valid_mesh_shape(self, shape):
        try:
            return mc.objExists(shape) and mc.nodeType(shape) == 'mesh' and not mc.getAttr(shape + '.intermediateObject')
        except Exception:
            return False

    def _get_valid_mesh_shapes_under(self, root):
        shapes = mc.listRelatives(root, ad=True, c=True, f=True, type='mesh') or []
        return [s for s in shapes if self._is_valid_mesh_shape(s)]

    def _get_valid_mesh_transform(self, node):
        # 输入 shape 或 transform，返回拥有至少一个有效 mesh shape 的 transform，否则 None
        if not mc.objExists(node):
            return None
        x = node
        if mc.nodeType(x) != 'transform':
            p = mc.listRelatives(x, p=True, f=True) or []
            x = p[0] if p else None
        if not x:
            return None
        shapes = mc.listRelatives(x, s=True, f=True) or []
        return x if any(self._is_valid_mesh_shape(s) for s in shapes) else None

    def _mesh_sig(self, shape):
        return (mc.polyEvaluate(shape, face=True), mc.polyEvaluate(shape, vertex=True))

    def _build_mesh_info(self, root):
        # 返回: shape -> dict(xform, sig, shortX, shortNoNS)
        info = {}
        for s in self._get_valid_mesh_shapes_under(root):
            x = self._get_valid_mesh_transform(s)
            if not x:
                continue
            info[s] = {
                'xform': x,
                'sig': self._mesh_sig(s),
                'shortX': self._short(x),
                'shortNoNS': self._no_ns(self._short(x)),
            }
        return info

    def _names_likely_same(self, a_short, b_short_nonns):
        # a_short：驱动 transform 短名（可能带命名空间）；b_short_nonns：目标 transform 短名（无命名空间）
        a = self._no_ns(a_short).lower()
        b = b_short_nonns.lower()
        if a == b:
            return True
        # 去尾部非字母数字符号
        a_base = re.sub(r'[\W_]+$', '', a)
        b_base = re.sub(r'[\W_]+$', '', b)
        if a_base == b_base:
            return True
        # 左右一致 + 常见部件关键词
        lr_pairs = [('eyel', 'eyel'), ('eyer', 'eyer'), ('_l', '_l'), ('_r', '_r'), ('l_', 'l_'), ('r_', 'r_')]
        parts = ['eye', 'ball', 'vitreous', 'brow', 'lash', 'tooth', 'teeth', 'rope', 'necklace', 'gauntlets', 'skirt', 'body', 'tongue']
        if any(la in a and lb in b for la, lb in lr_pairs) and any(k in a and k in b for k in parts):
            return True
        # 上/下牙一致
        if ('upteeth' in a and 'upteeth' in b) or ('lowteeth' in a and 'lowteeth' in b):
            return True
        return False

    def _pick_best_candidate(self, target_short_nonns, candidates, drv_info):
        # 优先短名去命名空间完全一致
        for s in candidates:
            if self._no_ns(drv_info[s]['shortX']) == target_short_nonns:
                return s
        # 次选名称近似
        for s in candidates:
            if self._names_likely_same(drv_info[s]['shortX'], target_short_nonns):
                return s
        # 否则取第一个
        return candidates[0] if candidates else None

    def _set_blend_weight(self, blend_node, driver_xform, value=1.0):
        # 尝试通过别名设置；若无，退回 weight[0]
        alias_direct = '{}.{}'.format(blend_node, self._short(driver_xform))
        try:
            if mc.objExists(alias_direct):
                mc.setAttr(alias_direct, value)
                return
            aliases = mc.aliasAttr(blend_node, q=True) or []
            a_map = dict(zip(aliases[::2], aliases[1::2]))  # alias -> plug
            d_short_nonns = self._no_ns(self._short(driver_xform))
            for alias in a_map.keys():
                if self._no_ns(alias) == d_short_nonns:
                    mc.setAttr('{}.{}'.format(blend_node, alias), value)
                    return
            # 回退：权重 0
            mc.setAttr('{}.w[0]'.format(blend_node), value)
        except Exception as e:
            # 最后回退
            try:
                mc.setAttr('{}.w[0]'.format(blend_node), value)
            except Exception:
                print("  ⚠️ 设置blendShape权重失败:", blend_node, "|", e)


# 可选：Script Editor 直接执行时的简单入口（选中：先目标组，后驱动组）
if __name__ == '__main__':
    sel = mc.ls(sl=True, l=True) or []
    if len(sel) != 2:
        mc.warning('请选择两个组：先选“目标组”（被驱动），再选“驱动组”（施加形变的来源）')
    else:
        mgr = BlendshapeManager()
        mgr.create_precise_blendshapes_between_groups(sel[0], sel[1])