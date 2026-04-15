import re

html_snippet = """  ## HTML Snippet with PDF Links

                                <div style="height:24px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div style="height:30px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div data-wp-interactive="core/file" class="wp-block-file">
                                    <object data-wp-bind--hidden="!state.hasPdfPreview" hidden class="wp-block-file__embed" data="https://yakama.com/wp-content/uploads/2026/02/YN-Govt-Ops-Newsletter-TBH-Issue-Q1-FY26.pdf" type="application/pdf" style="width:100%;height:600px" aria-label="Embed of YN Govt Ops Newsletter TBH Issue Q1 FY26."></object>
                                    <a id="wp-block-file--media-7b079c60-b8c3-44dc-abf3-170e7ad2804c" href="https://yakama.com/wp-content/uploads/2026/02/YN-Govt-Ops-Newsletter-TBH-Issue-Q1-FY26.pdf">YN Govt Ops Newsletter TBH Issue Q1 FY26</a>
                                    <a href="https://yakama.com/wp-content/uploads/2026/02/YN-Govt-Ops-Newsletter-TBH-Issue-Q1-FY26.pdf" class="wp-block-file__button wp-element-button" download aria-describedby="wp-block-file--media-7b079c60-b8c3-44dc-abf3-170e7ad2804c">Download</a>
                                </div>
                                <div style="height:29px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div data-wp-interactive="core/file" class="wp-block-file">
                                    <object data-wp-bind--hidden="!state.hasPdfPreview" hidden class="wp-block-file__embed" data="https://yakama.com/wp-content/uploads/2025/11/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q4-FY25.pdf" type="application/pdf" style="width:100%;height:600px" aria-label="Embed of YN Govt Ops Newsletter TBH Issue 2 Q4 FY25."></object>
                                    <a id="wp-block-file--media-0889a938-3176-4eb6-beff-dc0aa5295a3b" href="https://yakama.com/wp-content/uploads/2025/11/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q4-FY25.pdf">YN Govt Ops Newsletter TBH Issue 2 Q4 FY25</a>
                                    <a href="https://yakama.com/wp-content/uploads/2025/11/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q4-FY25.pdf" class="wp-block-file__button wp-element-button" download aria-describedby="wp-block-file--media-0889a938-3176-4eb6-beff-dc0aa5295a3b">Download</a>
                                </div>
                                <div style="height:28px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div data-wp-interactive="core/file" class="wp-block-file">
                                    <object data-wp-bind--hidden="!state.hasPdfPreview" hidden class="wp-block-file__embed" data="https://yakama.com/wp-content/uploads/2025/10/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q3-FY25.pdf" type="application/pdf" style="width:100%;height:600px" aria-label="Embed of YN Govt Ops Newsletter TBH Issue 2 Q3 FY25."></object>
                                    <a id="wp-block-file--media-8a3e6ffd-2d29-4c64-a461-787cfccd78b0" href="https://yakama.com/wp-content/uploads/2025/10/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q3-FY25.pdf">YN Govt Ops Newsletter TBH Issue 2 Q3 FY25</a>
                                </div>
                                <div style="height:34px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div data-wp-interactive="core/file" class="wp-block-file">
                                    <object data-wp-bind--hidden="!state.hasPdfPreview" hidden class="wp-block-file__embed" data="https://yakama.com/wp-content/uploads/2025/06/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q2-FY25.pdf" type="application/pdf" style="width:100%;height:600px" aria-label="Embed of YN Govt Ops Newsletter TBH Issue 2 Q2 FY25."></object>
                                    <a id="wp-block-file--media-a6e0d581-660b-46f5-9428-f95b7330ee84" href="https://yakama.com/wp-content/uploads/2025/06/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q2-FY25.pdf">YN Govt Ops Newsletter TBH Issue 2 Q2 FY25</a>
                                    <a href="https://yakama.com/wp-content/uploads/2025/06/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q2-FY25.pdf" class="wp-block-file__button wp-element-button" download aria-describedby="wp-block-file--media-a6e0d581-660b-46f5-9428-f95b7330ee84">Download</a>
                                </div>
                                <div style="height:38px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div style="height:39px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div data-wp-interactive="core/file" class="wp-block-file">
                                    <object data-wp-bind--hidden="!state.hasPdfPreview" hidden class="wp-block-file__embed" data="https://yakama.com/wp-content/uploads/2025/06/M21.010_YN-Press-Release_Trump-Termination-of-RCBA_Final-Corrected-6.12.25.pdf" type="application/pdf" style="width:100%;height:600px" aria-label="Embed of M21.010_YN Press Release_Trump Termination of RCBA_Final-Corrected (6.12.25)."></object>
                                    <a id="wp-block-file--media-410828fd-2d56-4a4c-b729-8db3dfba6b1e" href="https://yakama.com/wp-content/uploads/2025/06/M21.010_YN-Press-Release_Trump-Termination-of-RCBA_Final-Corrected-6.12.25.pdf">M21.010_YN Press Release_Trump Termination of RCBA_Final-Corrected (6.12.25)</a>
                                    <a href="https://yakama.com/wp-content/uploads/2025/06/M21.010_YN-Press-Release_Trump-Termination-of-RCBA_Final-Corrected-6.12.25.pdf" class="wp-block-file__button wp-element-button" download aria-describedby="wp-block-file--media-410828fd-2d56-4a4c-b729-8db3dfba6b1e">Download</a>
                                </div>
                                <div style="height:39px" aria-hidden="true" class="wp-block-spacer"></div>
                                <figure class="wp-block-image size-large">
                                    <img loading="lazy" decoding="async" width="1024" height="1024" src="https://yakama.com/wp-content/uploads/2025/06/airport_display-1024x1024.png" alt="" class="wp-image-15946" srcset="https://yakama.com/wp-content/uploads/2025/06/airport_display-1024x1024.png 1024w, https://yakama.com/wp-content/uploads/2025/06/airport_display-300x300.png 300w, https://yakama.com/wp-content/uploads/2025/06/airport_display-150x150.png 150w, https://yakama.com/wp-content/uploads/2025/06/airport_display-768x768.png 768w, https://yakama.com/wp-content/uploads/2025/06/airport_display-600x600.png 600w, https://yakama.com/wp-content/uploads/2025/06/airport_display-140x140.png 140w, https://yakama.com/wp-content/uploads/2025/06/airport_display-580x580.png 580w, https://yakama.com/wp-content/uploads/2025/06/airport_display-860x860.png 860w, https://yakama.com/wp-content/uploads/2025/06/airport_display.png 1080w" sizes="auto, (max-width: 1024px) 100vw, 1024px"/>
                                </figure>
                                <div style="height:42px" aria-hidden="true" class="wp-block-spacer"></div>
                                <figure class="wp-block-image size-large">
                                    <img loading="lazy" decoding="async" width="662" height="1024" src="https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-662x1024.png" alt="" class="wp-image-15834" srcset="https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-662x1024.png 662w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-194x300.png 194w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-768x1187.png 768w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-994x1536.png 994w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-1325x2048.png 1325w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-580x897.png 580w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-860x1329.png 860w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-1160x1793.png 1160w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-1320x2040.png 1320w, https://yakama.com/wp-content/uploads/2025/05/ALl-are-welcome-•-June-6-8-2025-4-scaled.png 1656w" sizes="auto, (max-width: 662px) 100vw, 662px"/>
                                </figure>
                                <div style="height:29px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div data-wp-interactive="core/file" class="wp-block-file">
                                    <object data-wp-bind--hidden="!state.hasPdfPreview" hidden class="wp-block-file__embed" data="https://yakama.com/wp-content/uploads/2025/04/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q1-FY25.pdf" type="application/pdf" style="width:100%;height:600px" aria-label="Embed of YN Govt Ops Newsletter TBH Issue 2 Q1 FY25."></object>
                                    <a id="wp-block-file--media-d1aad28a-0b83-4102-8219-378dbbf8ff32" href="https://yakama.com/wp-content/uploads/2025/04/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q1-FY25.pdf">YN Govt Ops Newsletter TBH Issue 2 Q1 FY25</a>
                                    <a href="https://yakama.com/wp-content/uploads/2025/04/YN-Govt-Ops-Newsletter-TBH-Issue-2-Q1-FY25.pdf" class="wp-block-file__button wp-element-button" download aria-describedby="wp-block-file--media-d1aad28a-0b83-4102-8219-378dbbf8ff32">Download</a>
                                </div>
                                <div style="height:32px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div style="height:24px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div style="height:22px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div data-wp-interactive="core/file" class="wp-block-file aligncenter">
                                    <object data-wp-bind--hidden="!state.hasPdfPreview" hidden class="wp-block-file__embed" data="https://yakama.com/wp-content/uploads/2024/04/YN-Press-Release_White-House-Water-Summit-final-4.23.24.pdf" type="application/pdf" style="width:100%;height:600px" aria-label="Embed of YN Press Release_White House Water Summit (final 4.23.24)."></object>
                                    <a id="wp-block-file--media-183cf9dd-db9a-4d17-944e-fff32956739f" href="https://yakama.com/wp-content/uploads/2024/04/YN-Press-Release_White-House-Water-Summit-final-4.23.24.pdf">YN Press Release_White House Water Summit (final 4.23.24)</a>
                                    <a href="https://yakama.com/wp-content/uploads/2024/04/YN-Press-Release_White-House-Water-Summit-final-4.23.24.pdf" class="wp-block-file__button wp-element-button" download aria-describedby="wp-block-file--media-183cf9dd-db9a-4d17-944e-fff32956739f">Download</a>
                                </div>
                                <div style="height:17px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div style="height:100px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div class="wp-block-buttons is-vertical is-layout-flex wp-container-core-buttons-is-layout-8cf370e7 wp-block-buttons-is-layout-flex"></div>
                                <div style="height:97px" aria-hidden="true" class="wp-block-spacer"></div>
                                <div style="height:26px" aria-hidden="true" class="wp-block-spacer"></div>
                                <h2 class="wp-block-heading has-text-align-center">Laliik Elk Hunt 2023</h2>
"""

# extract all PDF links from the HTML snippet
links = re.findall(r'href="(https?://[^"]+\.pdf)"', html_snippet)

# print the extracted links
print("\n".join(links))