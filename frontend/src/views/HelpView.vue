<script setup lang="ts">
import Accordion from 'primevue/accordion'
import AccordionContent from 'primevue/accordioncontent'
import AccordionHeader from 'primevue/accordionheader'
import AccordionPanel from 'primevue/accordionpanel'
import Tag from 'primevue/tag'
import { onMounted } from 'vue'
import { useSchema } from '../stores/schema'

const store = useSchema()
onMounted(() => store.load())
</script>

<template>
  <div class="page">
    <h1>MIB &amp; PUS guide</h1>
    <p class="muted">
      A crash course for everyone who has never worked with SCOS-2000, CCS5, PUS or a
      MIB before. Five minutes here will save hours later.
    </p>

    <div class="card">
      <h2>What is a MIB?</h2>
      <p>
        The <b>MIB (Mission Information Base)</b> is the configuration database of ESA
        ground systems such as <b>SCOS-2000</b> (mission control) and Terma's
        <b>CCS5</b> (checkout / EGSE). It is delivered as a set of plain-text,
        tab-separated files (<span class="mono">pcf.dat</span>,
        <span class="mono">pid.dat</span>, …) whose format is fixed by the ESA
        <i>SCOS-2000 Database Import ICD</i>. The MIB tells the ground system:
      </p>
      <ul>
        <li><b>Telemetry (TM)</b> — which packets your unit sends, where each parameter
          sits inside them, how to convert raw values to engineering values, and which
          values are out of limits.</li>
        <li><b>Telecommands (TC)</b> — which commands your unit accepts, what arguments
          they take, how to encode them into packets, and how to verify they worked.</li>
      </ul>
      <p>
        In a typical unit/instrument workflow, your MIB configures the EGSE (e.g. a
        CCS5-based SIS that bridges TC packets to your MIL-1553 bus and wraps bus data
        into TM packets), and is later merged by ESA into the spacecraft-wide MIB.
      </p>
    </div>

    <div class="card">
      <h2>The mental model</h2>
      <p>Everything in the MIB hangs off four ideas:</p>
      <ol>
        <li>
          <b>Parameters</b> (<span class="mono">pcf</span> for TM,
          <span class="mono">cpc</span> for TC): a named, typed value — "bus voltage,
          16-bit unsigned integer, volts".
        </li>
        <li>
          <b>Packets / commands</b> (<span class="mono">pid</span> /
          <span class="mono">ccf</span>): a container identified by APID + PUS
          type/subtype (+ SID for housekeeping).
        </li>
        <li>
          <b>Layout</b> (<span class="mono">plf</span>/<span class="mono">vpd</span> for
          TM, <span class="mono">cdf</span> for TC): which parameter sits at which
          byte/bit offset inside the container.
        </li>
        <li>
          <b>Semantics</b>: calibrations (raw ↔ engineering), limits, validity,
          verification — the layers that make numbers meaningful and operations safe.
        </li>
      </ol>
      <p class="muted small">
        The wizards in each project create all the linked records together, so you
        rarely need to touch the raw tables — but every table remains fully editable.
      </p>
    </div>

    <div class="card">
      <h2>What is PUS?</h2>
      <p>
        The <b>Packet Utilisation Standard</b> (ECSS-E-ST-70-41) standardises what TM/TC
        packets <i>mean</i>. Every packet carries a <b>service type</b> and
        <b>subtype</b>: housekeeping is service 3, events are service 5, "do something"
        commands are usually service 8, and so on. Each packet also belongs to an
        <b>APID</b> (Application Process ID) — the address of the on-board application
        (your unit). Below is the catalog of services this tool knows; the wizards
        pre-fill types and structures from it.
      </p>
      <Accordion>
        <AccordionPanel v-for="s in store.pusServices" :key="s.service" :value="String(s.service)">
          <AccordionHeader>Service {{ s.service }} — {{ s.name }}</AccordionHeader>
          <AccordionContent>
            <p>{{ s.help }}</p>
            <div v-if="s.tm.length">
              <b>TM reports:</b>
              <ul>
                <li v-for="st in s.tm" :key="st.subtype">
                  ({{ s.service }},{{ st.subtype }}) {{ st.name }}
                  <span v-if="st.note" class="muted small"> — {{ st.note }}</span>
                </li>
              </ul>
            </div>
            <div v-if="s.tc.length">
              <b>TC requests:</b>
              <ul>
                <li v-for="st in s.tc" :key="st.subtype">
                  ({{ s.service }},{{ st.subtype }}) {{ st.name }}
                  <span v-if="st.note" class="muted small"> — {{ st.note }}</span>
                </li>
              </ul>
            </div>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>
    </div>

    <div class="card">
      <h2>Parameter types (PTC / PFC)</h2>
      <p>
        Every parameter has a <b>PTC</b> (what kind of value) and a <b>PFC</b> (which
        size/encoding variant). You will meet these two numbers everywhere in the MIB.
        The wizards include a picker that translates plain language ("unsigned 16-bit
        integer") into the right pair.
      </p>
      <div v-for="t in store.ptcCatalog" :key="t.ptc" class="ptc-entry">
        <div>
          <Tag :value="`PTC ${t.ptc}`" />
          <b style="margin-left: 0.5rem">{{ t.name }}</b>
          <span class="muted small" style="margin-left: 0.5rem">
            {{ t.tm && t.tc ? 'TM + TC' : t.tm ? 'TM only' : 'TC only' }}
          </span>
        </div>
        <p class="small" style="margin: 0.25rem 0 0.75rem">{{ t.help }}</p>
      </div>
    </div>

    <div class="card">
      <h2>Recommended workflow for a unit MIB</h2>
      <ol>
        <li>Create a project (keep the starter content enabled — it sets up the PUS TC
          packet header and generic verification stages).</li>
        <li>Define your <b>TM parameters</b> (pcf) — or let the packet wizard create
          them as you go.</li>
        <li>Use the <b>packet wizard</b> for each housekeeping/event packet: it builds
          pid/pic/tpcf/plf with correct offsets.</li>
        <li>Add <b>calibrations</b> (status texts, sensor curves) and attach them to
          parameters.</li>
        <li>Use the <b>command wizard</b> for each telecommand: it builds ccf/cpc/cdf
          plus verification entries.</li>
        <li>Add <b>limit checks</b> for safety-relevant parameters.</li>
        <li><b>Validate</b> until there are no errors, then <b>export</b> the MIB zip —
          feed it to your SIS/CCS5 and deliver it to ESA.</li>
      </ol>
      <p class="muted small">
        Authoritative references: SCOS-2000 Database Import ICD
        (EGOS-MCS-S2K-ICD-0001, issue 7.0) and ECSS-E-ST-70-41C. Field-level help
        throughout this tool paraphrases the ICD; the section number is shown in each
        editor so you can look up the original text.
      </p>
    </div>
  </div>
</template>

<style scoped>
.ptc-entry { border-bottom: 1px solid var(--p-surface-200); padding: 0.5rem 0; }
.ptc-entry:last-child { border-bottom: none; }
</style>
